import time

import requests

# ---------------------------------------------------------------------------
# Switched from the old key-less IMDb API to https://mn-api-imdb.vercel.app/
# (single endpoint, two modes):
#   - Text search:  GET /api/search?q=<query>   -> {"Search": [...]}
#   - By IMDb id:   GET /api/search?id=<tt...>   -> flat details object
#
# ⚠️ IMPORTANT RELIABILITY NOTE (found via live testing):
#   The by-id endpoint is reliable for movies, but for TV series it has been
#   observed to either:
#     a) return the right Title but leave Year/Poster/Director/Writer/
#        Stars/Genres/Runtime all "N/A" (e.g. Game of Thrones, tt0944947) -
#        this is a genuine data gap on the API's side, nothing to retry -
#        that's simply all the detail it has for that title, or
#     b) return a COMPLETELY UNRELATED title for a valid, correctly
#        formatted id (requesting tt0903747 - Breaking Bad - returned the
#        1975 film "Mirror" instead, with an unrelated poster/plot/rating
#        attached).
#   An invalid/unknown id doesn't error either - it comes back as a "Title":
#   "IMDb <id>" object with every other field "N/A".
#
#   ✅ UPDATE: case (b) turned out to be intermittent rather than a fixed,
#   permanent mismatch for that id - retrying the same request sometimes
#   gets the correct title back. get_details() below now retries the by-id
#   lookup a few times specifically when the title doesn't match what's
#   already confirmed correct (via search_titles()'s cache) and uses the
#   first attempt that matches. If every attempt still comes back wrong,
#   it falls back to showing only the Title/Year/Poster we already trust
#   (from the cache) and drops the mismatched extra fields (Plot, rating,
#   cast, etc.) rather than showing details for the wrong title - case (a)
#   above is a genuine data gap on the API's side and isn't something a
#   retry can fix.
# ---------------------------------------------------------------------------

BASE_URL = "https://mn-api-imdb.vercel.app/api/search"

_title_cache = {}  # imdb_id -> {"Title": ..., "Year": ..., "Poster": ..., "Type": ...}

BY_ID_RETRY_ATTEMPTS = 3
BY_ID_RETRY_DELAY_SECONDS = 0.5


def _clean(value):
    """Treat missing/'N/A' the same as None so callers can skip it cleanly."""
    if not value or value == "N/A":
        return None
    return value


def _looks_related(known_title, returned_title):
    """Loose sanity check: does the by-id lookup's Title look like the
    title we already know for this id? Used to decide whether to trust the
    extra fields (Plot, rating, cast, ...) that came with it, and whether
    to retry the lookup (see get_details() below).
    """
    known_title = _clean(known_title)
    returned_title = _clean(returned_title)

    if not known_title or not returned_title:
        return True  # nothing to compare against - can't rule it out

    k = known_title.strip().lower()
    r = returned_title.strip().lower()

    return k in r or r in k


def _guess_type(raw_type):
    """Normalize the API's IMDb title-type strings ('feature', 'TV series',
    'TV mini-series', 'short', 'video', ...) down to just 'movie' or
    'series' for the rest of the bot."""
    if not raw_type:
        return None

    value = raw_type.strip().lower()

    if "series" in value or "episode" in value:
        return "series"

    return "movie"


def seed_title_cache(imdb_id, title=None, year=None, poster=None, media_type=None):
    """Remember known-good Title/Year/Poster/Type for an IMDb id, gathered
    from a search result or a saved watchlist entry, so get_details() can
    sanity-check the by-id lookup against it (see module notes above).
    """
    if not imdb_id:
        return

    entry = _title_cache.setdefault(imdb_id, {})

    if title:
        entry["Title"] = title
    if year and year != "N/A":
        entry["Year"] = year
    if poster and poster != "N/A":
        entry["Poster"] = poster
    if media_type:
        entry["Type"] = media_type


def search_titles(query):
    """Text search - GET /api/search?q=<query>.

    Returns a normalized list of dicts: Title, Year, imdbID, Type, Poster.
    Also seeds the title cache used by get_details() below, and skips any
    non-title rows the search occasionally mixes in (e.g. a person id like
    "in0000274" showing up instead of a "tt..." title id).
    """
    try:
        response = requests.get(BASE_URL, params={"q": query}, timeout=8)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    raw_results = data.get("Search") or []
    results = []

    for item in raw_results:
        imdb_id = item.get("imdbID")

        if not imdb_id or not imdb_id.startswith("tt"):
            continue  # skip junk / non-title rows

        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        poster = item.get("Poster")
        media_type = _guess_type(item.get("Type")) or "movie"

        seed_title_cache(imdb_id, title=title, year=year, poster=poster, media_type=media_type)

        results.append(
            {
                "Title": title,
                "Year": year,
                "imdbID": imdb_id,
                "Type": media_type,
                "Poster": poster,
            }
        )

    return results


def _fetch_by_id_once(imdb_id):
    try:
        response = requests.get(BASE_URL, params={"id": imdb_id}, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def get_details(imdb_id):
    """Full detail lookup - GET /api/search?id=<imdb_id>.

    See the reliability note at the top of this file for why the raw
    response isn't trusted blindly, and why it's retried a few times when
    the title doesn't match what's already confirmed correct.
    Returns None if the id can't be resolved to anything at all (matches
    the old API's "not found" shape).
    """
    cached = _title_cache.get(imdb_id, {})
    known_title = cached.get("Title")

    raw = None
    for attempt in range(BY_ID_RETRY_ATTEMPTS):
        candidate = _fetch_by_id_once(imdb_id)

        if candidate is None:
            break

        raw = candidate  # keep the latest response as the fallback

        if _looks_related(known_title, _clean(candidate.get("Title"))):
            break  # good match - stop retrying

        if attempt < BY_ID_RETRY_ATTEMPTS - 1:
            time.sleep(BY_ID_RETRY_DELAY_SECONDS)

    if not raw:
        return None

    raw_title = _clean(raw.get("Title"))
    raw_year = _clean(raw.get("Year"))
    raw_poster = _clean(raw.get("Poster"))
    raw_plot = _clean(raw.get("Plot"))
    raw_rating = _clean(raw.get("imdbRating"))

    # The API's own "not found" shape: everything N/A, Title like
    # "IMDb tt0000000". If we also have nothing cached, this id is dead.
    if not any([raw_year, raw_poster, raw_plot, raw_rating]) and not cached:
        return None

    title_reliable = _looks_related(known_title, raw_title)

    details = {
        "imdbID": imdb_id,
        "Title": known_title or raw_title or f"IMDb {imdb_id}",
        "Year": cached.get("Year") or raw_year or "N/A",
        "Poster": cached.get("Poster") or raw_poster or "N/A",
        "Type": cached.get("Type") or "movie",
        "Source": "imdb",
    }

    if title_reliable:
        details["Plot"] = raw_plot or "N/A"
        details["imdbRating"] = raw_rating or "N/A"
        details["Director"] = _clean(raw.get("Director")) or "N/A"
        details["Writer"] = _clean(raw.get("Writer")) or "N/A"
        details["Actors"] = _clean(raw.get("Stars")) or "N/A"
        details["Genre"] = _clean(raw.get("Genres")) or "N/A"
        details["Runtime"] = _clean(raw.get("Runtime")) or "N/A"
    else:
        # Every retry still came back with a different title than the one
        # we know this id actually is - don't show its extra fields.
        details["Plot"] = "N/A"
        details["imdbRating"] = "N/A"
        details["Director"] = "N/A"
        details["Writer"] = "N/A"
        details["Actors"] = "N/A"
        details["Genre"] = "N/A"
        details["Runtime"] = "N/A"

    # Fields this API never provides - kept as "N/A" keys so
    # utils/formatter.py's _clean() skips them the same way it always has.
    details["totalSeasons"] = "N/A"
    details["imdbVotes"] = "N/A"
    details["Rated"] = "N/A"
    details["Language"] = "N/A"
    details["Country"] = "N/A"
    details["Awards"] = "N/A"

    return details


def get_series_episode_count(imdb_id, total_seasons):
    """The new IMDb API doesn't return season/episode data at all, so this
    can no longer be computed. Always returns None - utils/formatter.py
    already omits the Episodes line whenever this is None.
    """
    return None
