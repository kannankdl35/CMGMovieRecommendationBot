import re

import requests

# ---------------------------------------------------------------------------
# IMDb API (https://imdb.iamidiotareyoutoo.com/docs/index.html)
# ---------------------------------------------------------------------------
# Free, key-less replacement for the old OMDb integration (services/omdb.py,
# now removed). Two GET endpoints are used, both under /search:
#
#   GET /search?q=<free text>   -> title/keyword search, up to several
#                                   basic matches (used for "Find Movies").
#   GET /search?tt=<imdb id>    -> direct lookup for a single title by its
#                                   IMDb ID (used for the details page).
#
# The direct-lookup response nests most of the useful data under two keys:
#   - "short"  - a schema.org-style JSON-LD block (name, genre, actor,
#                director, duration, description, aggregateRating, ...)
#   - "top"    - IMDb's own internal fields (titleType, releaseYear,
#                runtime, genres, ratingsSummary, plot, primaryImage, ...)
#
# This module normalizes both shapes into a single flat dict so the rest
# of the bot (utils/formatter.py, utils/ui.py, plugins/*) never has to
# know or care which key the data actually came from. Every field is
# best-effort: if the API omits something (or the whole request fails),
# the corresponding key is simply left out/None rather than raising, so a
# flaky response here can never crash the bot (Feature 1, 2 & 3).

BASE_URL = "https://imdb.iamidiotareyoutoo.com/search"

REQUEST_TIMEOUT = 10


def _get_json(params):
    """Shared best-effort GET + JSON parse for both endpoints below.
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
    'PT2H1M') into a '<n> min' string. Returns None if it can't be parsed."""
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
    list of Person objects (e.g. `short["actor"]` / `short["director"]`).
    Accepts a single dict, a list of dicts, or None."""
    if not people:
        return None

    if isinstance(people, dict):
        people = [people]

    names = [p.get("name") for p in people if isinstance(p, dict) and p.get("name")]

    return ", ".join(names) if names else None


def search_titles(query, page=1):
    """Search the IMDb API for movies/series matching `query`.

    Returns a list of basic result dicts: Title, Year, imdbID, Poster.
    Used for Feature 1 - Find Movies. Unlike the old OMDb search, this
    endpoint doesn't report whether each result is a movie/series/episode
    up front - callers that need to filter by type (or show it) fetch
    get_details() per result, same as they already do for the extra
    Language/Release-date line on search cards (utils/ui.py,
    plugins/inline.py).
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

    Any field the API doesn't provide is left as None so callers can skip
    it (see utils/formatter.py's _clean()). Returns None if the title
    couldn't be found/fetched at all.
    """
    if not imdb_id:
        return None

    data = _get_json({"tt": imdb_id})
    if not data:
        return None

    short = data.get("short") or {}
    top = data.get("top") or {}

    # A handful of deployments echo back the same basic shape used by
    # search_titles() (a "description" list) instead of / alongside
    # "short"/"top" for an ID lookup - fall back to that for whatever it
    # can offer rather than failing outright.
    basic = {}
    description = data.get("description")
    if isinstance(description, list) and description:
        basic = description[0]

    title = _first(top.get("title"), short.get("name"), basic.get("#TITLE"))
    if not title:
        return None

    # ---- Year -------------------------------------------------------
    release_year = top.get("releaseYear") or {}
    date_published = short.get("datePublished") or ""
    year = _first(
        release_year.get("year"),
        date_published[:4] if len(date_published) >= 4 else None,
        basic.get("#YEAR"),
    )

    # ---- Type (movie vs series) --------------------------------------
    title_type_raw = (top.get("titleType") or short.get("@type") or "").lower()
    media_type = "series" if "series" in title_type_raw else "movie"

    # ---- Runtime ------------------------------------------------------
    runtime_seconds = (top.get("runtime") or {}).get("seconds")
    if runtime_seconds:
        runtime = f"{int(runtime_seconds) // 60} min"
    else:
        runtime = _iso8601_duration_to_minutes(short.get("duration"))

    # ---- Genres ---------------------------------------------------------
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
    imdb_votes = _first(ratings_summary.get("voteCount"), short_rating.get("ratingCount"))

    # ---- Plot -------------------------------------------------------------
    plot_text = (top.get("plot") or {}).get("plotText") or {}
    plot = _first(plot_text.get("plainText"), short.get("description"))

    # ---- Poster -------------------------------------------------------------
    poster = _first((top.get("primaryImage") or {}).get("url"), short.get("image"), basic.get("#IMG_POSTER"))

    # ---- Language, content rating, director, cast --------------------------
    spoken_languages = (top.get("spokenLanguages") or {}).get("spokenLanguages") or []
    language = _first(
        ", ".join([l.get("text") for l in spoken_languages if isinstance(l, dict) and l.get("text")]) or None,
        short.get("inLanguage"),
    )
    rated = short.get("contentRating")
    director = _names(short.get("director"))
    actors = _names(short.get("actor"))

    # ---- Seasons / Episodes (series only) ------------------------------
    episodes_block = top.get("episodes") or {}
    seasons_list = episodes_block.get("seasons") or []
    total_seasons = len(seasons_list) if seasons_list else None

    episode_totals = episodes_block.get("episodes") or {}
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
    Unlike OMDb - which required looping over every season - the IMDb API
    used here reports an episode total directly on the details lookup, so
    this just re-fetches get_details() and reads it off. `total_seasons`
    is accepted but unused; it's kept purely so callers don't need to
    change how they invoke this.
    """
    details = get_details(imdb_id)
    if not details:
        return None

    return details.get("totalEpisodes")
