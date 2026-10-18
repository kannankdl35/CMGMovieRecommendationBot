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


def get_weekly_regional_releases():
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


def _fetch_all():
    combined = get_weekly_regional_releases()

    if not combined:
        combined = {lang: [] for lang in REGIONAL_LANGUAGES}

    combined["english"] = get_weekly_english_releases()

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
