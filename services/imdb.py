import re

import requests

from services.details import movie_details, series_details, find_by_imdb_id

# ---------------------------------------------------------------------------
# IMDb API (https://imdb.iamidiotareyoutoo.com/docs/index.html)
# ---------------------------------------------------------------------------
# Free, key-less replacement for the old OMDb integration (services/omdb.py,
# now removed). One GET endpoint is used for everything, under /search:
#
#   GET /search?q=<free text OR an imdb id, e.g. tt1375666>
#
# ✅ BUGFIX: an earlier version of this file called the ID-lookup case with
# a "tt=" parameter (`/search?tt=<id>`), which this API does not recognize -
# every details lookup silently failed as a result ("Could not find details
# for this title" on every Find Movies / Watchlist / Suggest Me details
# page). The correct call passes the id through the SAME "q" parameter used
# for text search - `/search?q=<id>` - confirmed against the live API.
#
# ✅ ALSO DISCOVERED: unlike OMDb, this API's response - even when looked up
# by exact IMDb ID - only ever contains a thin record:
#   #TITLE, #YEAR, #IMDB_ID, #RANK, #ACTORS, #AKA, #IMDB_URL, #IMG_POSTER
# There is no Runtime / Genre / Plot / Rating / Language / Seasons /
# Episodes data available from this API at all, by ID or by text search.
# To still deliver those fields (required by the details page), get_details()
# below resolves the same title on TMDB - already integrated in this bot
# for "Suggest Me" (services/details.py, same TMDB_API_KEY) - via TMDB's
# /find endpoint, and merges in whatever the free IMDb API doesn't have.
# Every field stays best-effort: if neither source has something, the key
# is simply left out/None rather than raising, so a flaky response here can
# never crash the bot (Feature 1, 2 & 3).

BASE_URL = "https://imdb.iamidiotareyoutoo.com/search"

REQUEST_TIMEOUT = 10

# A handful of common ISO 639-1 codes -> display names, used only to label
# TMDB's "original_language" (e.g. "en") when the free IMDb API doesn't
# have a Language field of its own for this title.
_LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi", "ml": "Malayalam", "ta": "Tamil",
    "te": "Telugu", "kn": "Kannada", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "es": "Spanish", "fr": "French", "it": "Italian",
    "de": "German", "ru": "Russian", "pt": "Portuguese", "ar": "Arabic",
}


def _get_json(params):
    """Shared best-effort GET + JSON parse for the /search endpoint.
    Returns the parsed response dict, or None on any failure (network
    error, non-200 status, invalid JSON, or an explicit ok=False)."""
    try:
        response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if not data or data.get("ok") is not True:
        return None

    return data


def _first(*values):
    """Return the first value that isn't missing/empty."""
    for value in values:
        if value not in (None, "", "N/A"):
            return value
    return None


def _iso8601_duration_to_minutes(duration):
    """Best-effort parse of an ISO-8601 duration string (e.g. 'PT121M',
    'PT2H1M') into a '<n> min' string. Returns None if it can't be parsed.
    (Kept for the rare case the free IMDb API's response ever does include
    a schema.org-style "short" block with a duration field.)"""
    if not duration or not isinstance(duration, str):
        return None

    match = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?$", duration)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    total_minutes = hours * 60 + minutes

    return f"{total_minutes} min" if total_minutes else None


def _names(people):
    """Extract a comma-separated list of names from a schema.org-style
    list of Person objects. Accepts a single dict, a list of dicts, or
    None. (Same rationale as _iso8601_duration_to_minutes above - kept as
    a best-effort extra in case a response ever includes it.)"""
    if not people:
        return None

    if isinstance(people, dict):
        people = [people]

    names = [p.get("name") for p in people if isinstance(p, dict) and p.get("name")]

    return ", ".join(names) if names else None


def search_titles(query, page=1):
    """Search the IMDb API for movies/series matching `query`.

    Returns a list of basic result dicts: Title, Year, imdbID, Poster.
    Used for Feature 1 - Find Movies. This endpoint doesn't report whether
    each result is a movie/series/episode up front - callers that need to
    filter by type (or show it) fetch get_details() per result, same as
    they already do for the extra Language/Release-date line on search
    cards (utils/ui.py, plugins/inline.py).
    """
    if not query:
        return []

    data = _get_json({"q": query})
    if not data:
        return []

    items = data.get("description") or []

    results = []
    for item in items:
        imdb_id = item.get("#IMDB_ID")
        if not imdb_id:
            continue

        results.append({
            "Title": item.get("#TITLE") or "Unknown",
            "Year": str(item.get("#YEAR")) if item.get("#YEAR") else "-",
            "imdbID": imdb_id,
            "Poster": item.get("#IMG_POSTER"),
        })

    return results


def get_details(imdb_id):
    """Fetch full details for a given IMDb ID, e.g. 'tt1375666', and
    normalize them into a flat dict with (best-effort) keys:

        Title, Year, Type ("movie"/"series"), Runtime, Genre, Rated,
        Language, Director, Actors, Plot, Poster, imdbRating, imdbVotes,
        totalSeasons, totalEpisodes, imdbID

    Two sources are combined:
      1. The free IMDb API (Title, Year, Poster, Actors - see module
         docstring above for why that's genuinely all it has).
      2. TMDB, resolved via services.details.find_by_imdb_id() (Runtime,
         Genre, Plot, Rating, Language, Seasons/Episodes).

    Any field neither source has is left as None so callers can skip it
    (see utils/formatter.py's _clean()). Returns None only if BOTH sources
    come up empty for this id - i.e. the title genuinely couldn't be
    found anywhere, not just that one API had a hiccup.
    """
    if not imdb_id:
        return None

    # ---- Source 1: the free IMDb API --------------------------------
    # ✅ BUGFIX: this used to be {"tt": imdb_id}, a parameter this API
    # doesn't recognize - every lookup silently failed. IMDb-ID lookups go
    # through the same "q" parameter as text search.
    data = _get_json({"q": imdb_id})
    short = (data or {}).get("short") or {}
    top = (data or {}).get("top") or {}
    basic = {}
    description = (data or {}).get("description") if data else None
    if isinstance(description, list) and description:
        basic = description[0]

    # ---- Source 2: TMDB (Runtime, Genre, Plot, Rating, Seasons, ...) ---
    tmdb_id, tmdb_type = find_by_imdb_id(imdb_id)
    tmdb_data = {}
    if tmdb_id and tmdb_type == "movie":
        tmdb_data = movie_details(tmdb_id) or {}
    elif tmdb_id and tmdb_type == "series":
        tmdb_data = series_details(tmdb_id) or {}

    title = _first(
        top.get("title"), short.get("name"), basic.get("#TITLE"),
        tmdb_data.get("title"), tmdb_data.get("name"),
    )
    if not title:
        # Neither the IMDb API nor TMDB knows this id - nothing to show.
        return None

    # ---- Year -------------------------------------------------------
    release_year = top.get("releaseYear") or {}
    date_published = short.get("datePublished") or ""
    tmdb_date = tmdb_data.get("release_date") or tmdb_data.get("first_air_date") or ""
    year = _first(
        release_year.get("year"),
        date_published[:4] if len(date_published) >= 4 else None,
        basic.get("#YEAR"),
        tmdb_date[:4] if len(tmdb_date) >= 4 else None,
    )

    # ---- Type (movie vs series) --------------------------------------
    # TMDB's /find already tells us this directly and reliably - prefer
    # it over guessing from the IMDb API's (usually absent) titleType.
    if tmdb_type in ("movie", "series"):
        media_type = tmdb_type
    else:
        title_type_raw = (top.get("titleType") or short.get("@type") or "").lower()
        media_type = "series" if "series" in title_type_raw else "movie"

    # ---- Runtime ------------------------------------------------------
    runtime = None
    if tmdb_type == "movie" and tmdb_data.get("runtime"):
        runtime = f"{tmdb_data['runtime']} min"
    elif tmdb_type == "series":
        episode_runtimes = tmdb_data.get("episode_run_time") or []
        if episode_runtimes:
            runtime = f"{episode_runtimes[0]} min"
    if not runtime:
        runtime_seconds = (top.get("runtime") or {}).get("seconds")
        if runtime_seconds:
            runtime = f"{int(runtime_seconds) // 60} min"
        else:
            runtime = _iso8601_duration_to_minutes(short.get("duration"))

    # ---- Genres ---------------------------------------------------------
    genres = [g.get("name") for g in (tmdb_data.get("genres") or []) if g.get("name")]
    if not genres:
        genre_entries = (top.get("genres") or {}).get("genres") or []
        genres = [g.get("text") for g in genre_entries if isinstance(g, dict) and g.get("text")]
    if not genres and short.get("genre"):
        raw_genre = short.get("genre")
        genres = raw_genre if isinstance(raw_genre, list) else [raw_genre]
    genre = ", ".join(genres) if genres else None

    # ---- Rating / votes -------------------------------------------------
    ratings_summary = top.get("ratingsSummary") or {}
    short_rating = short.get("aggregateRating") or {}
    imdb_rating = _first(ratings_summary.get("aggregateRating"), short_rating.get("ratingValue"))
    if imdb_rating in (None, "") and tmdb_data.get("vote_average"):
        imdb_rating = round(tmdb_data["vote_average"], 1)
    imdb_votes = _first(
        ratings_summary.get("voteCount"), short_rating.get("ratingCount"), tmdb_data.get("vote_count"),
    )

    # ---- Plot -------------------------------------------------------------
    plot_text = (top.get("plot") or {}).get("plotText") or {}
    plot = _first(plot_text.get("plainText"), short.get("description"), tmdb_data.get("overview"))

    # ---- Poster -------------------------------------------------------------
    poster = _first((top.get("primaryImage") or {}).get("url"), short.get("image"), basic.get("#IMG_POSTER"))
    if not poster and tmdb_data.get("poster_path"):
        poster = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

    # ---- Language, content rating, director, cast --------------------------
    spoken_languages = (top.get("spokenLanguages") or {}).get("spokenLanguages") or []
    language = _first(
        ", ".join([l.get("text") for l in spoken_languages if isinstance(l, dict) and l.get("text")]) or None,
        short.get("inLanguage"),
        _LANGUAGE_NAMES.get(tmdb_data.get("original_language")),
        tmdb_data.get("original_language"),
    )
    rated = short.get("contentRating")
    director = _names(short.get("director"))
    # "#ACTORS" is one of the few fields the free IMDb API's search-by-ID
    # actually returns - prefer it over the (usually absent) schema.org one.
    actors = _first(basic.get("#ACTORS"), _names(short.get("actor")))

    # ---- Seasons / Episodes (series only) ------------------------------
    total_seasons = None
    total_episodes = None
    if tmdb_type == "series":
        total_seasons = tmdb_data.get("number_of_seasons")
        total_episodes = tmdb_data.get("number_of_episodes")
    if not total_seasons:
        episodes_block = top.get("episodes") or {}
        seasons_list = episodes_block.get("seasons") or []
        total_seasons = len(seasons_list) if seasons_list else None
    if not total_episodes:
        episode_totals = (top.get("episodes") or {}).get("episodes") or {}
        total_episodes = episode_totals.get("total") if isinstance(episode_totals, dict) else None

    return {
        "Title": title,
        "Year": str(year) if year else "-",
        "Type": media_type,
        "Runtime": runtime,
        "Genre": genre,
        "Rated": rated,
        "Language": language,
        "Director": director,
        "Actors": actors,
        "Plot": plot,
        "Poster": poster,
        "imdbRating": str(imdb_rating) if imdb_rating not in (None, "") else None,
        "imdbVotes": str(imdb_votes) if imdb_votes not in (None, "") else None,
        "totalSeasons": str(total_seasons) if total_seasons else None,
        "totalEpisodes": total_episodes,
        "imdbID": imdb_id,
    }


def get_series_episode_count(imdb_id, total_seasons=None):
    """Return the total number of episodes for a series, or None if it
    can't be determined.

    Kept as a separate function (same signature as the old OMDb version)
    for compatibility with existing call sites in plugins/details.py.
    get_details() already resolves this (via TMDB, see above), so this
    just re-fetches it and reads it off. `total_seasons` is accepted but
    unused; it's kept purely so callers don't need to change how they
    invoke this.
    """
    details = get_details(imdb_id)
    if not details:
        return None

    return details.get("totalEpisodes")
