import requests
from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"

REQUEST_TIMEOUT = 10

def movie_details(movie_id):
    """Fetch detailed movie information from TMDB API.

    Note: TMDB's /movie/{id} response already includes a top-level
    "imdb_id" field by default (no append_to_response needed), which
    Suggest Me uses to show the same IMDb API-based details page used by
    Find Movies & Series (Feature 2).
    """
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None

# ✅ NEW FUNCTION: Fetch TV series details
def series_details(series_id):
    """Fetch detailed TV series information from TMDB API.

    ✅ CHANGED (Feature 2): appends "external_ids" so the response includes
    the title's IMDb ID (nested under data["external_ids"]["imdb_id"]).
    Unlike /movie/{id}, TMDB's /tv/{id} does not return an IMDb ID by
    default, and Suggest Me needs it to show the same IMDb API-based details
    page (Trailer / Watchlist / Done buttons) used by Find Movies & Series.
    """
    url = f"{BASE_URL}/tv/{series_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "external_ids",
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None


# ✅ NEW FUNCTION (bugfix): Find a TMDB id from an IMDb id.
#
# The free IMDb API used for search (services/imdb.py, wired up in place of
# OMDb) turns out to only ever return a thin record when looked up by ID -
# Title, Year, Poster, and a short Cast string, nothing else. It has no
# Runtime / Genre / Plot / Rating / Seasons / Episodes data at all, so
# services/imdb.py's get_details() calls this to resolve the same title on
# TMDB (already integrated here, same API key as Suggest Me) and enrich the
# details page with everything the free IMDb API can't provide.
def find_by_imdb_id(imdb_id):
    """Look up the TMDB id + media type ("movie" or "series") for a given
    IMDb id via TMDB's /find endpoint.

    Returns (tmdb_id, "movie"/"series"), or (None, None) if TMDB has no
    match (or the request fails) - callers should treat that as "no
    enrichment available" rather than an error.
    """
    if not imdb_id:
        return None, None

    url = f"{BASE_URL}/find/{imdb_id}"
    params = {"api_key": TMDB_API_KEY, "external_source": "imdb_id"}

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return None, None

    if response.status_code != 200:
        return None, None

    try:
        data = response.json()
    except ValueError:
        return None, None

    movie_results = data.get("movie_results") or []
    if movie_results:
        return movie_results[0].get("id"), "movie"

    tv_results = data.get("tv_results") or []
    if tv_results:
        return tv_results[0].get("id"), "series"

    return None, None
