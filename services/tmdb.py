import requests

from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"


def discover_movies(
    genre=None,
    language=None,
    rating=None,
    page=1
):
    """
    Discover movies using TMDb filters.
    """

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 500,
        "page": page
    }

    if genre:
        params["with_genres"] = genre

    if language:
        params["with_original_language"] = language

    if rating:
        params["vote_average.gte"] = rating

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()

    return None
