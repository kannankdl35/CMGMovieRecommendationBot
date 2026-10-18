import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from services.tmdb import search_titles_tmdb, get_weekly_english_releases

# ---------------------------------------------------------------------------
# 📅 OTT Releases This Week (see keyboards/ott_releases.py for the main-menu
# entry point and plugins/callback.py for everything these buttons trigger).
#
# Two data sources, merged into one dict keyed by language:
#   - Malayalam/Tamil/Telugu/Kannada/Hindi: scraped from
#     ottreleasesthisweek.com. Confirmed live: each release is an <h3>
#     title heading immediately followed by a <ul> whose <li> items are
#     "Release Date:", "OTT Platform:", "Language:", "Genre:" (each label
#     bolded, value as plain text after it - hence read via
#     li.get_text(" ", strip=True) and split on the first colon, not a
#     single-line regex).
#   - English: services.tmdb.get_weekly_english_releases() (TMDb's Digital
#     release-type filter is dense and reliable for English/US, unlike the
#     same filter's sparse results for Indian regional languages).
#
# get_cached_ott_releases() below refreshes this at most every
# CACHE_TTL_SECONDS and serves every user from that cached copy - so this
# has no per-request cost and no rate-limit concern, unlike every
# commercial release-calendar API tested for this.
#
# This is a LAZY refresh: it only re-scrapes when a request happens to
# come in after the cache has gone stale. That's why it's also pushed
# PROACTIVELY, twice a day, by services/release_scheduler.py (started in
# bot.py) - so the list updates on schedule even if no user opens the
# menu right when it goes stale. CACHE_TTL_SECONDS below matches that
# scheduler's cadence, so this lazy path is just a safety net if the
# background task ever dies.
# ---------------------------------------------------------------------------

log = logging.getLogger(__name__)

HOMEPAGE_URL = "https://ottreleasesthisweek.com/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REGIONAL_LANGUAGES = ["malayalam", "tamil", "telugu", "kannada", "hindi"]
ALL_LANGUAGES = REGIONAL_LANGUAGES + ["english"]

CACHE_TTL_SECONDS = 12 * 60 * 60  # twice a day
EMPTY_RETRY_SECONDS = 5 * 60  # if a refresh came back empty, retry after 5 min

REQUIRED_FIELDS = {"release date", "language"}  # platform/genre optional

# How many regional languages a post's entries must collectively cover to
# count as "the general roundup" rather than a single-language post (see
# _looks_like_multi_language_roundup() below) - 3 of 5 leaves room for a
# week where the roundup happens to be missing 1-2 languages while still
# clearly not a Telugu-only/Hollywood-only post.
MIN_LANGUAGES_FOR_ROUNDUP = 3

# How many of the homepage's newest post links to check before giving up.
# The general roundup is normally the 1st or 2nd link (Telugu-only and
# English-only posts are interleaved with it), so this is generous
# headroom without risking a slow/expensive scrape on every refresh.
MAX_HOMEPAGE_CANDIDATES = 8

_cache = {"data": None, "fetched_at": None}


def _iter_candidate_post_urls():
    """Post links from the homepage.

    The site now links posts from anchors that are NOT inside <h2>/<h3>
    (or that wrap the heading), so we take every same-site, single-segment
    slug link (e.g. /this-week-in-indiaoctober-12-172026/) and skip
    category/tag/nav pages. Posts whose slug mentions "india" (the general
    roundup) are tried first, then the rest in page order (newest first).
    """
    response = requests.get(HOMEPAGE_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    skip_slugs = {
        "blog", "about-us", "contact-us", "privacy-policy", "terms-and-conditions",
        "disclaimer", "feed", "wp-json", "wp-content", "author", "page",
    }
    seen = set()
    urls = []

    for link in soup.find_all("a", href=True):
        href = link["href"].split("#")[0].split("?")[0]
        if not href.startswith("http"):
            if href.startswith("/"):
                href = HOMEPAGE_URL.rstrip("/") + href
            else:
                continue
        if "ottreleasesthisweek.com" not in href or href in seen:
            continue
        seen.add(href)

        path = href.split("ottreleasesthisweek.com", 1)[1].strip("/")
        if not path or "/" in path or path in skip_slugs:
            continue
        if path.startswith(("category", "tag", "wp-")):
            continue
        if not any(ch.isdigit() for ch in path):
            continue  # real weekly posts always carry a date in the slug

        urls.append(href)

    urls.sort(key=lambda u: 0 if "india" in u.lower() else 1)  # stable sort
    return urls[:MAX_HOMEPAGE_CANDIDATES]


def _looks_like_multi_language_roundup(entries):
    """True if these entries collectively cover at least
    MIN_LANGUAGES_FOR_ROUNDUP of the 5 regional languages - this is what
    actually distinguishes the general roundup post (every language mixed
    together) from a single-language post like a Telugu-only or
    English/Hollywood-only week, regardless of what the post happens to
    be titled or slugged this particular week.
    """
    languages_seen = set()

    for entry in entries:
        language_field = entry.get("language", "").lower()
        for lang in REGIONAL_LANGUAGES:
            if lang in language_field:
                languages_seen.add(lang)

    return len(languages_seen) >= MIN_LANGUAGES_FOR_ROUNDUP


def _parse_fields_from_list(ul_tag):
    """Read a <ul>'s <li> children as "Label: value" pairs - the label is
    bolded (a separate text node from the value), so get_text(" ", ...)
    joins them with a space and we split on the first colon rather than
    matching a single contiguous "Label: value" line."""
    fields = {}

    for li in ul_tag.find_all("li"):
        text = li.get_text(" ", strip=True)
        if ":" not in text:
            continue
        label, _, value = text.partition(":")
        fields[label.strip().lower()] = value.strip()

    return fields


def _extract_release_blocks(html):
    """Walk h2/h3/h4 headings and <ul> elements in document order (NOT via
    DOM siblings - the heading and its field list aren't direct siblings
    on this site, they're both inside a shared wrapper). Each heading
    becomes the "current title" until a <ul> right after it contains all
    four expected fields, at which point that's recorded as one release
    entry - this naturally skips nav lists, "Also read" links, and the
    page's own top-level h2 title (which has no such <ul> right after it).
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup

    entries = []
    current_title = None

    for element in body.find_all(["h2", "h3", "h4", "ul"]):
        if element.name in ("h2", "h3", "h4"):
            current_title = element.get_text(strip=True)
            continue

        if element.name == "ul" and current_title:
            fields = _parse_fields_from_list(element)

            if REQUIRED_FIELDS <= set(fields.keys()):
                entries.append(
                    {
                        "title": current_title,
                        "release_date": fields["release date"],
                        "platform": fields.get("ott platform") or fields.get("platform") or fields.get("ott") or "",
                        "language": fields["language"],
                        "genre": fields.get("genre", ""),
                        # Resolved lazily only if/when a user taps this
                        # entry - see resolve_release_key() below.
                        "key_id": None,
                    }
                )
                current_title = None  # consumed - don't reuse for a later unrelated <ul>

    return entries


def _get_regional_from_ottrw():
    """Fetch this week's regional-language OTT releases.

    Returns a dict keyed by language -> list of release entries. A
    pan-Indian release tagged with multiple languages appears in every
    matching language's list. Returns {} on any failure (site down,
    layout changed, network error, no candidate post looked like a
    roundup) - get_cached_ott_releases() below is what actually protects
    users from that, by keeping serving the last good cached copy
    instead.
    """
    try:
        candidate_urls = _iter_candidate_post_urls()
    except Exception as e:
        log.error("OTT: homepage fetch failed: %r", e)
        return {}

    log.warning("OTT: %d candidate posts: %s", len(candidate_urls), candidate_urls)

    entries = None
    all_entries = []

    for post_url in candidate_urls:
        try:
            response = requests.get(post_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            candidate_entries = _extract_release_blocks(response.text)
        except Exception as e:
            log.error("OTT: failed to fetch/parse %s: %r", post_url, e)
            continue

        log.warning("OTT: %s -> %d entries", post_url, len(candidate_entries))

        if _looks_like_multi_language_roundup(candidate_entries):
            entries = candidate_entries
            break

        if len(all_entries) < 200 and candidate_urls.index(post_url) < 4:
            all_entries.extend(candidate_entries)

    if entries is None and all_entries:
        # No single roundup post found - merge the newest posts instead of
        # showing nothing, de-duplicated by title + date.
        seen_keys = set()
        entries = []
        for e in all_entries:
            k = (e["title"].lower(), e["release_date"])
            if k not in seen_keys:
                seen_keys.add(k)
                entries.append(e)
        log.warning("OTT: using merged newest posts (%d entries)", len(entries))

    if entries is None:
        log.error("OTT: nothing parsed from %d candidate posts", len(candidate_urls))
        return {}

    by_language = {lang: [] for lang in REGIONAL_LANGUAGES}

    for entry in entries:
        language_field = entry["language"].lower()
        for lang in REGIONAL_LANGUAGES:
            if lang in language_field:
                by_language[lang].append(entry)

    return by_language


WINDOW_DAYS_BACK = 10    # keep releases up to a week old...
WINDOW_DAYS_AHEAD = 21   # ...and up to a week ahead


def _parse_release_date(text):
    """'October 14, 2026' -> date, or None if it can't be parsed."""
    from datetime import datetime

    text = (text or "").strip().replace("Sept ", "Sep ")
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# PRIMARY SOURCE: Sacnilk's weekly "New OTT Releases This Week" articles.
# They list every release of the current week with date, platform and
# languages in clean tables, and a new one is published each week.
#   - Newest articles are discovered from https://www.sacnilk.com/tag/OTT
#   - Each article has (a) 10 featured titles, each in a table with
#     "Genre: / Platform: / Language:" under an "OTT Release: <date>" line,
#     and (b) a big "Date | Title | OTT Platform | Language" table.
# ottreleasesthisweek.com (above) is kept only as a fallback.
# ---------------------------------------------------------------------------

SACNILK_TAG_URL = "https://www.sacnilk.com/tag/OTT"
SACNILK_WEEKLY_RE = re.compile(r"ott[-_]releases[-_]this[-_]week", re.I)
SACNILK_ARTICLES = 3  # newest weekly articles to read

_LABEL_END = r"(?=Genre:|Platform:|Language:|Running Time:|No\. of Episodes:|IMDb|View Box|\||$)"


def _sacnilk_weekly_urls():
    r = requests.get(SACNILK_TAG_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0].split("?")[0]
        if href.startswith("/"):
            href = "https://www.sacnilk.com" + href
        if "sacnilk.com/news/" not in href or not SACNILK_WEEKLY_RE.search(href):
            continue
        if href not in urls:
            urls.append(href)
    return urls[:SACNILK_ARTICLES]


def _field(text, label):
    m = re.search(label + r":\s*(.*?)\s*" + _LABEL_END, text, re.S)
    return m.group(1).strip() if m else ""


def _parse_sacnilk_article(html):
    from datetime import datetime

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("h1") or soup.find("title")
    years = re.findall(r"(20\d\d)", title_tag.get_text(" ", strip=True) if title_tag else "")
    year = years[-1] if years else str(time.localtime().tm_year)

    entries = []
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)

        # (a) featured block: one table per title
        if "Platform:" in text and "Language:" in text:
            platform = _field(text, "Platform")
            language = _field(text, "Language")
            heading = table.find_previous(["h3", "h2"])
            title = re.sub(r"^\s*\d+\.\s*", "", heading.get_text(" ", strip=True)) if heading else ""
            date_node = table.find_previous(string=re.compile(r"OTT Release:", re.I))
            dm = re.search(r"([A-Z][a-z]+\.? \d{1,2},? \d{4})", date_node or "")
            if title and dm and platform:
                d = _parse_release_date(dm.group(1).replace(".", "").replace(",", ",").replace(" ,", ","))
                if d is None:
                    d = _parse_release_date(re.sub(r"(\d),? (\d{4})", r"\1, \2", dm.group(1)))
                if d:
                    entries.append({
                        "title": title, "release_date": d.strftime("%b %d, %Y"),
                        "platform": platform, "language": language,
                        "genre": _field(text, "Genre"), "key_id": None, "_date": d,
                    })
            continue

        # (b) big table: Date | Title | OTT Platform | Language
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td"])]
            if len(cells) < 4 or cells[0].lower() == "date":
                continue
            try:
                d = datetime.strptime(f"{cells[0]} {year}", "%b %d %Y").date()
            except ValueError:
                continue
            entries.append({
                "title": cells[1], "release_date": d.strftime("%b %d, %Y"),
                "platform": cells[2], "language": cells[3],
                "genre": "", "key_id": None, "_date": d,
            })
    return entries


def _get_regional_from_sacnilk():
    from datetime import date, timedelta

    try:
        urls = _sacnilk_weekly_urls()
    except Exception as e:
        log.error("OTT(sacnilk): tag page failed: %r", e)
        return {}
    log.warning("OTT(sacnilk): articles %s", urls)

    today = date.today()
    lo, hi = today - timedelta(days=WINDOW_DAYS_BACK), today + timedelta(days=WINDOW_DAYS_AHEAD)

    found, seen = [], set()
    for u in urls:
        try:
            r = requests.get(u, headers=HEADERS, timeout=20)
            r.raise_for_status()
            items = _parse_sacnilk_article(r.text)
        except Exception as e:
            log.error("OTT(sacnilk): %s failed: %r", u, e)
            continue
        log.warning("OTT(sacnilk): %s -> %d entries", u, len(items))
        for e in items:
            key = (e["title"].lower(), e["_date"])
            if key in seen or not (lo <= e["_date"] <= hi):
                continue
            if "outside india" in e["platform"].lower():
                continue  # rentals not available in India
            seen.add(key)
            found.append(e)

    found.sort(key=lambda e: e["_date"], reverse=True)
    by_language = {lang: [] for lang in REGIONAL_LANGUAGES + ["english"]}
    for e in found:
        lf = e["language"].lower()
        for lang in by_language:
            if lang in lf:
                by_language[lang].append(e)
    return by_language


def get_weekly_regional_releases():
    """Sacnilk first, then the old ottreleasesthisweek.com scraper."""
    data = _get_regional_from_sacnilk()
    if any(data.get(l) for l in REGIONAL_LANGUAGES):
        return data
    log.warning("OTT: sacnilk gave nothing, falling back to ottreleasesthisweek.com")
    return _get_regional_from_ottrw()


def _fetch_all():
    combined = get_weekly_regional_releases()

    if not combined:
        combined = {lang: [] for lang in REGIONAL_LANGUAGES}

    # English: TMDb list + English titles from the weekly articles, merged
    # and de-duplicated by title (neither source alone is complete).
    merged, seen = [], set()
    for entry in (get_weekly_english_releases() or []) + combined.get("english", []):
        key = (entry.get("title") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(entry)
    combined["english"] = merged

    return combined


def get_cached_ott_releases(force_refresh=False):
    """Return this week's OTT releases for all 6 languages, refreshing at
    most once every CACHE_TTL_SECONDS (12h - see release_scheduler.py for
    the proactive twice-daily push). If a refresh attempt comes back completely empty
    (site down, TMDb error) and there's already a previous good cache,
    that previous cache keeps being served rather than wiped out - a
    transient failure should degrade to "yesterday's list", not "no list".
    """
    now = time.time()
    last = _cache["fetched_at"]
    has_data = _cache["data"] is not None and any(
        _cache["data"].get(lang) for lang in ALL_LANGUAGES
    )
    # A cache that is empty is only trusted for a few minutes, so one
    # failed scrape can never leave users with "No releases" for 12 hours.
    ttl = CACHE_TTL_SECONDS if has_data else EMPTY_RETRY_SECONDS
    stale = last is None or (now - last) > ttl

    if force_refresh or stale:
        fresh = _fetch_all()
        has_any = any(fresh.get(lang) for lang in ALL_LANGUAGES)

        if has_any or _cache["data"] is None:
            _cache["data"] = fresh
            _cache["fetched_at"] = now
        else:
            # Refresh failed but we have an older good copy: keep serving
            # it, but retry soon instead of waiting another 12h.
            _cache["fetched_at"] = now - CACHE_TTL_SECONDS + EMPTY_RETRY_SECONDS

    return _cache["data"] or {lang: [] for lang in ALL_LANGUAGES}


def resolve_release_key(entry):
    """For a scraped regional entry (key_id starts out None), try to
    resolve a real TMDb key via a title search - called lazily, only when
    a user actually taps into that entry (plugins/callback.py's
    "ott_sel_" handler), so this cost is per-user-tap, not per-day-refresh.

    English entries already carry a real key_id from
    services.tmdb.get_weekly_english_releases() and are returned as-is.

    Returns a "tmdb_movie_<id>"/"tmdb_tv_<id>" key, or None if no
    confident match was found (caller falls back to a plain info card
    built from the scraped fields - see plugins/callback.py).
    """
    if entry.get("key_id"):
        return entry["key_id"]

    title = entry.get("title")
    if not title:
        return None

    candidates = search_titles_tmdb(title)
    if not candidates:
        return None

    wanted = title.strip().lower()

    for candidate in candidates:
        candidate_title = (candidate.get("Title") or "").strip().lower()
        if wanted == candidate_title or wanted in candidate_title or candidate_title in wanted:
            return candidate.get("imdbID")

    return None
