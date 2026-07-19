import re

import requests

# ---------------------------------------------------------------------------
# IMDb API (https://imdb.iamidiotareyoutoo.com/docs/index.html)
# ---------------------------------------------------------------------------
# Free, key-less API used for EVERYTHING title-related in this bot: search
# results/list ("Find Movies & Series"), the full details page (Find
# Movies & Series, Watchlist, and — after a title is picked — Suggest Me
# too), poster, cast, genres, runtime, rating, etc.
#
# ✅ CHANGED: this module used to also call out to TMDB (services/details.py)
# on every single get_details() call to fill in Runtime/Genre/Plot/Rating/
# Language/Seasons/Episodes, because the free IMDb API's search-by-ID used
# to look "thin" when only a couple of fields were being read out of it.
# That's been replaced: every field below is now pulled straight out of
# this API's own response (the "top" and "short" blocks already carry a
# LOT more than the few fields the old code read), and NO request to TMDB
# is made from here anymore. TMDB is now used ONLY to build/sort the
# "Suggest Me" recommendation list (services/tmdb.py + services/discover.py)
# — never to source movie/series details or the search list.
#
# This also fixes a real bug: the old get_details() made up to 3 sequential
# blocking HTTP calls (this API + TMDB /find + TMDB /movie or /tv). The
# inline "Find Movies & Series" search called that once PER search result
# (up to 20) before answering the inline query, which could take well over
# a minute — Telegram had already invalidated the query id by the time the
# bot tried to answer it (-> "QUERY_ID_INVALID" / no results shown in the
# inline list). Cutting this down to a single request per lookup, and
# fetching in parallel on the caller side (see plugins/inline.py), fixes
# that.
#
# ✅ FIX (details page showing almost nothing): get_details() was calling
# this API with the ID passed through the `q` (free-text search) query
# param instead of the `tt` (direct-by-ID) param. `q=<text>` only ever
# returns the lightweight "description" list (Title/Year/Poster/Actors) —
# no "top"/"short" blocks come back for it. `tt=<imdb_id>` is the lookup
# mode that returns the full "top" (runtime, genres, rating, plot,
# language, certificate, credits, episodes, etc.) and "short" (schema.org
# JSON-LD) blocks this file reads from below. That's why every field
# other than Poster/Actors/Title was silently coming back None before.
#
# NOTE ON FIELD NAMES: the exact shape of "top"/"short" below was mapped
# out empirically against the live API for the fields the previous version
# of this file already used (Title/Year/Runtime/Genre/Rating/Plot/Poster/
# Language/Seasons/Episodes — all confirmed working). The additional
# fields added below (Country, Director, Writer, Content Rating/Certificate)
# follow the same nesting style IMDb's data uses elsewhere in this
# response and are written defensively — if a key doesn't exist for a
# given title (or the API's shape differs slightly from what's assumed
# here), the field just comes back None and is skipped by the formatter,
# it will never crash the bot. If you find one of these doesn't populate
# for a title you know has that data, print(data) once in _get_json() to
# see the raw response and adjust the key path below.

BASE_URL = "https://imdb.iamidiotareyoutoo.com/search"

REQUEST_TIMEOUT = 10

# A handful of common ISO 639-1 codes -> display names, used only as a
# fallback if the API ever hands back a bare language code (e.g. "en")
# instead of a display name (e.g. "English").
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
    list of Person objects. Accepts a single dict, a list of dicts, or
    None."""
    if not people:
        return None

    if isinstance(people, dict):
        people = [people]

    names = [p.get("name") for p in people if isinstance(p, dict) and p.get("name")]

    return ", ".join(names) if names else None


def _text_list(entries, key="text"):
    """Extract a comma-separated list of `key` values from a list of
    dicts, e.g. genres.genres -> [{"text": "Horror"}, ...] -> "Horror,
    Comedy". Returns None if nothing usable is found."""
    if not entries:
        return None

    values = [e.get(key) for e in entries if isinstance(e, dict) and e.get(key)]

    return ", ".join(values) if values else None


def _language_display(value):
    """Map a bare language code (e.g. 'en') to a display name ('English')
    when possible; otherwise return the value as-is."""
    if not value:
        return None
    if isinstance(value, str) and len(value) <= 3 and value.lower() in _LANGUAGE_NAMES:
        return _LANGUAGE_NAMES[value.lower()]
    return value


def _principal_credits(top, category_names):
    """Pull names out of IMDb's "principalCredits" block for a given
    credit category (e.g. {"director", "directors"} or {"writer",
    "writers"}).

    Expected shape (best-effort — see module note above):
        top["principalCredits"] = [
            {"category": {"text": "Director"}, "credits": [
                {"name": {"nameText": {"text": "Jane Doe"}}}, ...
            ]},
            ...
        ]

    Returns a comma-separated name string, or None if this block isn't
    present in the response / doesn't match the expected shape.
    """
    credit_groups = top.get("principalCredits") if isinstance(top, dict) else None
    if not credit_groups:
        return None

    wanted = {c.lower() for c in category_names}

    for group in credit_groups:
        if not isinstance(group, dict):
            continue
        category_text = ((group.get("category") or {}).get("text") or "").lower()
        if category_text not in wanted:
            continue

        names = []
        for credit in group.get("credits") or []:
            if not isinstance(credit, dict):
                continue
            name_text = ((credit.get("name") or {}).get("nameText") or {}).get("text")
            if name_text:
                names.append(name_text)

        if names:
            return ", ".join(names)

    return None


def search_titles(query, page=1):
    """Search the IMDb API for movies/series matching `query`.

    Returns a list of basic result dicts: Title, Year, imdbID, Poster.
    Used for Feature 1 - Find Movies, and by find_imdb_id_by_title_year()
    below to resolve a "Suggest Me" (TMDB) title to an IMDb id.

    Uses the `q` (free-text) query param - this is the one meant for
    title searches. Do not use this for ID lookups; see get_details()
    below for that.
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
        Language, Country, Director, Writer, Actors, Plot, Poster,
        imdbRating, imdbVotes, totalSeasons, totalEpisodes, imdbID

    Sourced ENTIRELY from the free IMDb API — no TMDB calls are made here.
    Any field the API doesn't have for this title is left as None so
    callers can skip it (see utils/formatter.py's _clean()). Returns None
    only if the title genuinely couldn't be found.
    """
    if not imdb_id:
        return None

    # ---------------------------------------------------------------
    # ✅ FIX: ID lookups must use the `tt` query parameter, not `q`.
    #
    # This API has two distinct lookup modes:
    #   - `?q=<text>`  -> free-text title search (used by search_titles()
    #                     above) - returns only the lightweight
    #                     "description" list (Title/Year/Poster/Actors),
    #                     with NO "top"/"short" blocks attached.
    #   - `?tt=<id>`   -> direct-by-ID lookup - returns the full "top"
    #                     (IMDb GraphQL-style data: runtime, genres,
    #                     rating, plot, language, certificate, credits,
    #                     episodes, etc.) and "short" (schema.org JSON-LD)
    #                     blocks this function reads from below.
    #
    # get_details() was calling `?q=<imdb_id>` (passing e.g. "tt1375666"
    # as a plain search string), which the API mostly treats as a text
    # query - it can still resolve to the right title in "description",
    # but "top"/"short" come back empty, so every field this function
    # reads out of them (Runtime, Genre, Rating, Plot, Language, Country,
    # Director, Writer, Awards, Seasons/Episodes) silently fell back to
    # None and got skipped by the formatter - only the couple of fields
    # sourced from "description" (Title/Actors/Poster) ever showed up.
    # Switching to `tt=` fixes this without touching search_titles() or
    # any TMDB-related code.
    # ---------------------------------------------------------------
    data = _get_json({"tt": imdb_id})
    if not data:
        # Safety net only - `tt=` should always be the one that returns
        # the full "top"/"short" blocks; this just guards against ever
        # regressing to "no details at all" if that ever isn't true.
        data = _get_json({"q": imdb_id})
    if not data:
        return None

    short = data.get("short") or {}
    top = data.get("top") or {}
    basic = {}
    description = data.get("description")
    if isinstance(description, list) and description:
        basic = description[0]

    title = _first(top.get("title"), short.get("name"), basic.get("#TITLE"))
    if not title:
        # Nothing usable came back for this id.
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
    title_type_raw = (
        (top.get("titleType") or {}).get("id")
        or (top.get("titleType") or {}).get("text")
        or short.get("@type")
        or ""
    ).lower()
    media_type = "series" if ("series" in title_type_raw or "tvminiseries" in title_type_raw) else "movie"

    # ---- Runtime ------------------------------------------------------
    runtime_seconds = (top.get("runtime") or {}).get("seconds")
    if runtime_seconds:
        runtime = f"{int(runtime_seconds) // 60} min"
    else:
        runtime = _iso8601_duration_to_minutes(short.get("duration"))

    # ---- Genres ---------------------------------------------------------
    genre = _text_list((top.get("genres") or {}).get("genres"))
    if not genre and short.get("genre"):
        raw_genre = short.get("genre")
        genre = ", ".join(raw_genre) if isinstance(raw_genre, list) else raw_genre

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

    # ---- Language -----------------------------------------------------------
    spoken_languages = (top.get("spokenLanguages") or {}).get("spokenLanguages") or []
    language = _first(_text_list(spoken_languages), _language_display(short.get("inLanguage")))

    # ---- Content rating (certificate) ----------------------------------------
    rated = _first(
        (top.get("certificate") or {}).get("rating"),
        short.get("contentRating"),
    )

    # ---- Country of origin -----------------------------------------------
    country = _text_list((top.get("countriesOfOrigin") or {}).get("countries"))

    # ---- Director / Writer -------------------------------------------------
    director = _first(
        _principal_credits(top, {"director", "directors"}),
        _names(short.get("director")),
    )
    writer = _first(
        _principal_credits(top, {"writer", "writers"}),
        _names(short.get("creator")),
    )

    # "#ACTORS" is one of the few fields the free IMDb API's search-by-ID
    # reliably returns - prefer it, then fall back to principal credits /
    # the schema.org "actor" block.
    actors = _first(
        basic.get("#ACTORS"),
        _principal_credits(top, {"star", "stars", "actor", "actors"}),
        _names(short.get("actor")),
    )

    # ---- Awards (best-effort - not consistently present) ---------------
    award_summary = top.get("awardSummary") or top.get("awardsSummary") or {}
    wins = award_summary.get("wins") if isinstance(award_summary, dict) else None
    nominations = award_summary.get("nominations") if isinstance(award_summary, dict) else None
    awards = None
    if wins or nominations:
        parts = []
        if wins:
            parts.append(f"{wins} win{'s' if wins != 1 else ''}")
        if nominations:
            parts.append(f"{nominations} nomination{'s' if nominations != 1 else ''}")
        awards = " & ".join(parts)

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
        "Country": country,
        "Director": director,
        "Writer": writer,
        "Actors": actors,
        "Awards": awards,
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

    `total_seasons` is accepted but unused; kept purely so callers don't
    need to change how they invoke this.
    """
    details = get_details(imdb_id)
    if not details:
        return None

    return details.get("totalEpisodes")


def find_imdb_id_by_title_year(title, year=None):
    """Resolve a plain title (+ optional year) to an IMDb id via the free
    IMDb API's search endpoint.

    Used by "Suggest Me" (plugins/details.py's send_suggested_details()):
    TMDB is only used there to build/sort the recommendation list itself
    (services/tmdb.py) - once the user picks one of the suggested titles,
    this looks the SAME title up on the free IMDb API so the details page
    it opens is sourced from IMDb like every other details page in the
    bot, instead of a second TMDB lookup.

    Picks the first search result whose Year matches `year` (when given);
    falls back to the first result overall otherwise. Returns None if the
    title can't be found at all.
    """
    if not title:
        return None

    results = search_titles(title)
    if not results:
        return None

    if year:
        year_str = str(year)[:4]
        for item in results:
            if item.get("Year") == year_str:
                return item.get("imdbID")

    return results[0].get("imdbID")
