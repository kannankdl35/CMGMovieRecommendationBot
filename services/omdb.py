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


# ---------------------------------------------------------------------------
# ✅ NEW: Series episode count (Feature 1)
# ---------------------------------------------------------------------------
# OMDb's main "by ID" lookup (get_details above) only returns a
# "totalSeasons" field - there is no single field with the total episode
# count for a series. The only way to get that is to ask OMDb for each
# season individually (`Season=N`) and add up how many episodes it lists.

MAX_SEASONS_TO_FETCH = 30  # safety cap so a very long-running show can't stall the bot


def get_series_episode_count(imdb_id, total_seasons):
    """Return the total number of episodes for a series by summing the
    episode count of every season, or None if it couldn't be determined.

    `total_seasons` is the "totalSeasons" value already returned by
    get_details() for this title.
    """
    try:
        total_seasons_int = int(total_seasons)
    except (TypeError, ValueError):
        return None

    if total_seasons_int <= 0:
        return None

    seasons_to_fetch = min(total_seasons_int, MAX_SEASONS_TO_FETCH)

    total_episodes = 0
    found_any = False

    for season_num in range(1, seasons_to_fetch + 1):
        params = {
            "apikey": OMDB_API_KEY,
            "i": imdb_id,
            "Season": season_num,
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
        except requests.RequestException:
            continue

        if response.status_code != 200:
            continue

        data = response.json()

        if data.get("Response") != "True":
            continue

        total_episodes += len(data.get("Episodes", []))
        found_any = True

    return total_episodes if found_any else None
