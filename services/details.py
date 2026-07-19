import requests
from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"

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
