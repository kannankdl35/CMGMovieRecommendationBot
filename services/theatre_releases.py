import time
from datetime import date, timedelta

import requests

from config import TMDB_API_KEY

# ---------------------------------------------------------------------------
# 🎬 Theatre Release (see keyboards/upcoming.py + plugins/callback.py for
# the bot-facing side). Upcoming theatrical releases by language, via
# TMDb's discover/movie with the Theatrical release-type filter
# (with_release_type=2|3 - "Theatrical (limited)" and "Theatrical").
#
# Same underlying mechanism as services/tmdb.py's get_weekly_english_releases()
# (which uses with_release_type=4, Digital) - confirmed to work for that
# case; this hasn't been separately verified live yet, so treat the first
# real run as a test, same as everything else built this conversation.
#
# Cached per-language, refreshed at most once every CACHE_TTL_SECONDS - see
# get_cached_theatre_releases() below. Same as services/ott_releases.py,
# this cache is lazily refreshed on request, and is also pushed
# proactively twice a day by services/release_scheduler.py (started in
# bot.py) so the list updates on schedule regardless of traffic.
# ---------------------------------------------------------------------------

BASE_URL = "https://api.themoviedb.org/3"

LANGUAGE_CODES = {
    "malayalam": "ml",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn",
    "hindi": "hi",
    "english": "en",
}

# How far ahead "upcoming" looks. Wider than the OTT branch's fixed
# "this week" window, since theatrical listings are sparser per language
# (see chat history: a 7-day window for regional languages returned very
# few titles) - 30 days gives a more useful list without claiming to be
# "trending"/"popular", just genuinely upcoming.
LOOKAHEAD_DAYS = 30

CACHE_TTL_SECONDS = 12 * 60 * 60  # twice a day

_cache = {}  # lang -> {"data": [...], "fetched_at": <epoch seconds>}


def get_upcoming_theatre_releases(lang):
    """Upcoming theatrical releases for one language, sorted soonest-first
    (primary_release_date.asc - "upcoming" should be ordered by when it's
    actually releasing, not by popularity). Returns [] on any failure or
    unrecognized language.
    """
    code = LANGUAGE_CODES.get(lang)
    if not code:
        return []

    region = "US" if lang == "english" else "IN"
    today = date.today()
    future = today + timedelta(days=LOOKAHEAD_DAYS)

    try:
        response = requests.get(
            f"{BASE_URL}/discover/movie",
            params={
                "api_key": TMDB_API_KEY,
                "region": region,
                "with_release_type": "2|3",
                "release_date.gte": str(today),
                "release_date.lte": str(future),
                "with_original_language": code,
                "sort_by": "primary_release_date.asc",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    results = []

    for item in data.get("results", [])[:15]:
        tmdb_id = item.get("id")
        title = item.get("title") or "Unknown"
        release_date = item.get("release_date") or "N/A"

        results.append(
            {
                "title": title,
                "release_date": release_date,
                "key_id": f"tmdb_movie_{tmdb_id}",
            }
        )

    return results


def get_cached_theatre_releases(lang, force_refresh=False):
    """Same lazy-refresh pattern as
    services.ott_releases.get_cached_ott_releases() (12h TTL, pushed
    proactively twice a day by release_scheduler.py), but keyed per
    language, since each language is a separate TMDb request here (unlike
    the OTT branch's single scraped page covering all regional languages
    at once).
    """
    now = time.time()
    entry = _cache.setdefault(lang, {"data": None, "fetched_at": None})

    stale = (
        entry["data"] is None
        or entry["fetched_at"] is None
        or (now - entry["fetched_at"]) > CACHE_TTL_SECONDS
    )

    if force_refresh or stale:
        fresh = get_upcoming_theatre_releases(lang)
        if fresh or entry["data"] is None:
            entry["data"] = fresh
            entry["fetched_at"] = now

    return entry["data"] or []
