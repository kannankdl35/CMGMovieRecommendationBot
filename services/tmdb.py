import requests

from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"


def discover_movies(
    genre_id: int,
    language: str,
    rating: float,
    page: int = 1
):
    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": False,
        "include_video": False,
        "page": page,
        "with_original_language": language,
        "with_genres": genre_id,
        "vote_average.gte": rating,
        "vote_count.gte": 100
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    return response.json()
