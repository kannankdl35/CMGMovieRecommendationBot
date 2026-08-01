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

HOMEPAGE_URL = "https://ottreleasesthisweek.com/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; personal Telegram bot; "
        "fetches once daily for a cached release list)"
    )
}

REGIONAL_LANGUAGES = ["malayalam", "tamil", "telugu", "kannada", "hindi"]
ALL_LANGUAGES = REGIONAL_LANGUAGES + ["english"]

CACHE_TTL_SECONDS = 12 * 60 * 60  # twice a day

REQUIRED_FIELDS = {"release date", "ott platform", "language", "genre"}

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
    """Post links from the homepage, newest first, in the order the posts
    themselves are listed - NOT header/footer navigation.

    Previously this filtered by checking whether "india" appeared in the
    URL slug - that broke the week the site published the general roundup
    as "Upcoming OTT Releases this week July 27-Aug 1" (slug
    "ott-releases-this-week-july-27-aug-1", no "india" in it at all),
    silently falling back to the OLDER "...-in-india-..." post from the
    previous week and showing a stale list. The site's title/slug wording
    for the general roundup isn't consistent enough to key off of, so
    instead this just returns candidates in homepage order and
    get_weekly_regional_releases() below picks the first one whose actual
    scraped CONTENT looks like the multi-language roundup.

    Only links found inside an <h2> are considered - on this site every
    actual post title in the homepage feed is wrapped in an <h2> (that's
    how the "View Full List" post list renders), while the header/footer
    nav (Blog, About us, Contact us, Privacy Policy, social links, the
    site logo linking back to "/") is plain text/paragraph links, not
    headings. Without this restriction those nav links would get treated
    as "candidate posts" and checked (and wasted as failed HTTP requests)
    before ever reaching the real posts.
    """
    response = requests.get(HOMEPAGE_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen = set()
    urls = []

    for heading in soup.find_all("h2"):
        link = heading.find("a", href=True)
        if not link:
            continue

        href = link["href"]
        if href in seen:
            continue
        seen.add(href)

        if "ottreleasesthisweek.com" not in href:
            continue
        if "/category/" in href or "/tag/" in href:
            continue
        if href.rstrip("/") == HOMEPAGE_URL.rstrip("/"):
            continue

        urls.append(href)
        if len(urls) >= MAX_HOMEPAGE_CANDIDATES:
            break

    return urls


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
                        "platform": fields["ott platform"],
                        "language": fields["language"],
                        "genre": fields["genre"],
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
    except Exception:
        return {}

    entries = None

    for post_url in candidate_urls:
        try:
            response = requests.get(post_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            candidate_entries = _extract_release_blocks(response.text)
        except Exception:
            # This particular post failed to fetch/parse - try the next
            # newest candidate rather than giving up entirely.
            continue

        if _looks_like_multi_language_roundup(candidate_entries):
            entries = candidate_entries
            break

    if entries is None:
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
    stale = (
        _cache["data"] is None
        or _cache["fetched_at"] is None
        or (now - _cache["fetched_at"]) > CACHE_TTL_SECONDS
    )

    if force_refresh or stale:
        fresh = _fetch_all()
        has_any = any(fresh.get(lang) for lang in ALL_LANGUAGES)

        if has_any or _cache["data"] is None:
            _cache["data"] = fresh
            _cache["fetched_at"] = now

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
