import requests

from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"


def movie_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()

    return None
