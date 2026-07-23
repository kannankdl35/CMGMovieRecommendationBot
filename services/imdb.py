import requests

# ---------------------------------------------------------------------------
# ✅ CHANGED: switched from the old key-less IMDb API to
# https://mn-api-imdb.vercel.app/ (single endpoint, two modes):
#   - Text search:  GET /api/search?q=<query>   -> {"Search": [...]}
#   - By IMDb id:   GET /api/search?id=<tt...>   -> flat details object
#
# ⚠️ IMPORTANT RELIABILITY NOTE (found via live testing before writing this):
#   The by-id endpoint is reliable for movies, but for TV series it has been
#   observed to either:
#     a) return the right Title but leave Year/Poster/Director/Writer/
#        Stars/Genres/Runtime all "N/A" (e.g. Game of Thrones, tt0944947), or
#     b) return a COMPLETELY UNRELATED title for a valid, correctly
#        formatted id (requesting tt0903747 - Breaking Bad - returned the
#        1975 film "Mirror" instead, with an unrelated poster/plot/rating
#        attached).
#   An invalid/unknown id doesn't error either - it comes back as a "Title":
#   "IMDb <id>" object with every other field "N/A".
#
#   To avoid ever showing a user details for the wrong movie/show, this
#   module keeps a small in-memory cache of the Title/Year/Poster/Type
#   already confirmed correct by search_titles() (which has been reliable
#   in testing), and get_details() below:
#     - always prefers that cached Title/Year/Poster/Type over whatever the
#       by-id lookup returns, when known
#     - only keeps the EXTRA fields the by-id lookup adds (Plot, rating,
#       cast, etc.) if the title it returned actually looks like the title
#       we already know - otherwise those are dropped rather than shown
#       attached to the wrong title.
#   The cache is only populated during this process's lifetime (a bot
#   restart clears it) - if a bare id shows up with nothing cached for it
#   (e.g. an old watchlist entry after a restart), this falls back to
#   trusting the API's own Title for that one lookup.
# ---------------------------------------------------------------------------

BASE_URL = "https://mn-api-imdb.vercel.app/api/search"

_title_cache = {}  # imdb_id -> {"Title": ..., "Year": ..., "Poster": ..., "Type": ...}


def _clean(value):
    """Treat missing/'N/A' the same as None so callers can skip it cleanly."""
    if not value or value == "N/A":
        return None
    return value


def _looks_related(known_title, returned_title):
    """Loose sanity check: does the by-id lookup's Title look like the
    title we already know for this id? Used to decide whether to trust the
    extra fields (Plot, rating, cast, ...) that came with it.
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


def _fetch_by_id(imdb_id):
    try:
        response = requests.get(BASE_URL, params={"id": imdb_id}, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def get_details(imdb_id):
    """Full detail lookup - GET /api/search?id=<imdb_id>.

    See the reliability note at the top of this file for why the raw
    response isn't trusted blindly. Returns None if the id can't be
    resolved to anything at all (matches the old API's "not found" shape).
    """
    raw = _fetch_by_id(imdb_id)

    if not raw:
        return None

    cached = _title_cache.get(imdb_id, {})

    raw_title = _clean(raw.get("Title"))
    raw_year = _clean(raw.get("Year"))
    raw_poster = _clean(raw.get("Poster"))
    raw_plot = _clean(raw.get("Plot"))
    raw_rating = _clean(raw.get("imdbRating"))

    # The API's own "not found" shape: everything N/A, Title like
    # "IMDb tt0000000". If we also have nothing cached, this id is dead.
    if not any([raw_year, raw_poster, raw_plot, raw_rating]) and not cached:
        return None

    known_title = cached.get("Title")
    title_reliable = _looks_related(known_title, raw_title)

    details = {
        "imdbID": imdb_id,
        "Title": known_title or raw_title or f"IMDb {imdb_id}",
        "Year": cached.get("Year") or raw_year or "N/A",
        "Poster": cached.get("Poster") or raw_poster or "N/A",
        "Type": cached.get("Type") or "movie",
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
        # The by-id lookup's extra fields belong to a different title than
        # the one we know this id actually is - don't show them.
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
