import requests

from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"


def discover_movies(genre_id, language, rating, page=1):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "vote_average.gte": rating,
        "vote_count.gte": 100,
        "include_adult": False,
        "include_video": False,
        "with_original_language": language,
        "with_genres": genre_id,
        "page": page,
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()

    return None


def discover_series(genre_id, language, rating, page=1):

    url = f"{BASE_URL}/discover/tv"

    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "vote_average.gte": rating,
        "vote_count.gte": 100,
        "include_adult": False,
        "with_original_language": language,
        "with_genres": genre_id,
        "page": page,
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()

    return None
