import requests

from config import TMDB_API_KEY

# ---------------------------------------------------------------------------
# Backend for the "SEARCH - TMDb" button (see keyboards/home.py +
# plugins/inline.py), doing the same job as services/imdb.py's
# search_titles()/get_details() but sourced from TMDb instead - so
# "SEARCH - TMDb" follows the exact same workflow as "SEARCH - IMDb" (type a
# title inline, tap a result, see the same kind of details page).
#
# ✅ A title found via SEARCH - TMDb is always re-opened (from the
# Watchlist, etc.) using THIS module again, never services/imdb.py - see
# plugins/details.py's fetch_details() and plugins/callback.py's watchlist
# handlers, which key everything off the "tmdb_" prefix on the id itself
# rather than trying to resolve a "real" IMDb id for it.
# ---------------------------------------------------------------------------

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def _poster_url(path):
    return f"{IMAGE_BASE_URL}{path}" if path else None


def _clean(value):
    if not value or value == "N/A":
        return None
    return value


def search_titles_tmdb(query):
    """Text search via TMDb's multi-search (movies + TV in one call).

    Normalized to the same shape as services.imdb.search_titles():
    Title, Year, imdbID, Type, Poster.

    `imdbID` here is actually a composite TMDb key - "tmdb_movie_603" or
    "tmdb_tv_1396" - not a real IMDb id. Everywhere else in the bot just
    treats this key as an opaque id - see plugins/details.py's
    fetch_details(), which is what actually knows a "tmdb_" prefix means
    "look this one up on TMDb instead of IMDb".
    """
    try:
        response = requests.get(
            f"{BASE_URL}/search/multi",
            params={"api_key": TMDB_API_KEY, "query": query, "include_adult": "false"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    results = []

    for item in data.get("results", []):
        media_type = item.get("media_type")

        if media_type not in ("movie", "tv"):
            continue  # skip "person" rows mixed into multi-search results

        title = item.get("title") or item.get("name") or "Unknown"
        date = item.get("release_date") or item.get("first_air_date") or ""
        year = date[:4] if date else "N/A"
        poster = _poster_url(item.get("poster_path"))
        key_id = f"tmdb_{media_type}_{item.get('id')}"

        results.append(
            {
                "Title": title,
                "Year": year,
                "imdbID": key_id,
                "Type": "series" if media_type == "tv" else "movie",
                "Poster": poster,
            }
        )

    return results


def get_details_tmdb(key_id):
    """Full detail lookup for a TMDb-sourced key_id
    ("tmdb_movie_603" / "tmdb_tv_1396", built by search_titles_tmdb() above).

    Fetches /movie/{id} or /tv/{id} with credits appended, for
    Director/Writer/Cast. Returns None if the id can't be parsed or the
    lookup 404s.
    """
    try:
        _, media_type, tmdb_id = key_id.split("_", 2)
    except ValueError:
        return None

    endpoint = "tv" if media_type == "tv" else "movie"

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "append_to_response": "credits"},
            timeout=8,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    title = data.get("title") or data.get("name") or "Unknown"
    date = data.get("release_date") or data.get("first_air_date") or ""
    year = date[:4] if date else "N/A"

    genres = ", ".join(g["name"] for g in data.get("genres", [])) or None

    if media_type == "tv":
        runtime_list = data.get("episode_run_time") or []
        runtime_val = runtime_list[0] if runtime_list else None
    else:
        runtime_val = data.get("runtime")

    runtime = f"{runtime_val} min" if runtime_val else None

    credits_data = data.get("credits") or {}
    crew = credits_data.get("crew") or []
    cast = credits_data.get("cast") or []

    director = next((c.get("name") for c in crew if c.get("job") == "Director"), None)
    writer = next(
        (c.get("name") for c in crew if "writ" in (c.get("job") or "").lower()), None
    )
    actors = ", ".join(c.get("name") for c in cast[:5] if c.get("name")) or None

    country = ", ".join(c.get("name") for c in data.get("production_countries", [])) or None

    rating = data.get("vote_average")
    rating = f"{rating:.1f}" if isinstance(rating, (int, float)) and rating else None

    details = {
        "imdbID": key_id,
        "Title": title,
        "Year": year or "N/A",
        "Poster": _poster_url(data.get("poster_path")) or "N/A",
        "Plot": _clean(data.get("overview")) or "N/A",
        "imdbRating": rating or "N/A",  # shown as "TMDb Rating" - see utils/formatter.py
        "Director": director or "N/A",
        "Writer": writer or "N/A",
        "Actors": actors or "N/A",
        "Genre": genres or "N/A",
        "Runtime": runtime or "N/A",
        "Type": "series" if media_type == "tv" else "movie",
        "totalSeasons": str(data.get("number_of_seasons")) if data.get("number_of_seasons") else "N/A",
        "imdbVotes": "N/A",
        "Rated": "N/A",
        "Language": (data.get("original_language") or "N/A").upper(),
        "Country": country or "N/A",
        "Awards": "N/A",
        "Source": "tmdb",
        # Read directly by plugins/details.py instead of going through
        # services.imdb.get_series_episode_count() (which doesn't apply to
        # TMDb-sourced titles) - TMDb gives this for free.
        "_total_episodes": data.get("number_of_episodes"),
    }

    return details
