import requests

from config import OMDB_API_KEY

BASE_URL = "http://www.omdbapi.com/"


def search_titles(query, page=1):
    """Search OMDb (IMDb data) for movies/series matching `query`.
    Returns a list of basic result dicts: Title, Year, imdbID, Type, Poster.
    Used for Feature 1 - Find Movies.
    """
    params = {
        "apikey": OMDB_API_KEY,
        "s": query,
        "page": page,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    data = response.json()

    if data.get("Response") != "True":
        return []

    # Only keep movies and series (drop "episode" type results)
    results = [
        item for item in data.get("Search", [])
        if item.get("Type") in ("movie", "series")
    ]

    return results


def get_details(imdb_id):
    """Fetch full OMDb details (Feature 2) for a given IMDb ID, e.g. 'tt1375666'."""
    params = {
        "apikey": OMDB_API_KEY,
        "i": imdb_id,
        "plot": "full",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    if data.get("Response") != "True":
        return None

    return data
