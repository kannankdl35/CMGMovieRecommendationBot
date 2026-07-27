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
# get_cached_ott_releases() below refreshes this ONCE A DAY (lazily, on
# first request after the cache goes stale) and serves every user from
# that cached copy - so this has no per-request cost and no rate-limit
# concern, unlike every commercial release-calendar API tested for this.
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

CACHE_TTL_SECONDS = 24 * 60 * 60

REQUIRED_FIELDS = {"release date", "ott platform", "language", "genre"}

_cache = {"data": None, "fetched_at": None}


def _find_latest_india_post_url():
    """The homepage lists posts newest-first, mixing general "India"
    roundups (all regional languages together) with Telugu-only and
    English/Hollywood-only posts. The general roundup's slug reliably
    contains "india" - this returns the first (newest) matching link.
    """
    response = requests.get(HOMEPAGE_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href in seen:
            continue
        seen.add(href)

        if "ottreleasesthisweek.com" not in href:
            continue
        if "/category/" in href or "/tag/" in href:
            continue

        slug = href.rstrip("/").rsplit("/", 1)[-1].lower()
        if "india" in slug:
            return href

    return None


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
    layout changed, network error) - get_cached_ott_releases() below is
    what actually protects users from that, by keeping serving the last
    good cached copy instead.
    """
    try:
        post_url = _find_latest_india_post_url()
        if not post_url:
            return {}

        response = requests.get(post_url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        entries = _extract_release_blocks(response.text)
    except Exception:
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
    most once every 24h. If a refresh attempt comes back completely empty
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
