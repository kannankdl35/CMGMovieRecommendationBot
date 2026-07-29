import random
from datetime import date, timedelta

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
        date_str = item.get("release_date") or item.get("first_air_date") or ""
        year = date_str[:4] if date_str else "N/A"
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
    date_str = data.get("release_date") or data.get("first_air_date") or ""
    year = date_str[:4] if date_str else "N/A"

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


# ---------------------------------------------------------------------------
# 🔥 Trending Now (see keyboards/trending.py + plugins/callback.py)
# ---------------------------------------------------------------------------


def get_trending_tmdb(period="day"):
    """Fetch TMDb's trending titles for `period` ("day" or "week"),
    covering both movies and TV series in a single call
    (/trending/all/{period}).

    Normalized to the same shape as search_titles_tmdb(): Title, Year,
    imdbID (a "tmdb_movie_<id>"/"tmdb_tv_<id>" key, same convention as the
    rest of this module), Type, Poster.

    Returns up to 10 items (movie/tv only - "person" rows that can appear
    in /trending/all/* are skipped, same as search_titles_tmdb()).

    Returns None on any request failure (network error, bad API key,
    non-2xx response) so callers can tell "API failed" apart from "API
    succeeded but there's nothing trending" (an empty list).
    """
    try:
        response = requests.get(
            f"{BASE_URL}/trending/all/{period}",
            params={"api_key": TMDB_API_KEY},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    results = []

    for item in data.get("results", []):
        media_type = item.get("media_type")

        if media_type not in ("movie", "tv"):
            continue  # skip "person" rows mixed into /trending/all/*

        title = item.get("title") or item.get("name") or "Unknown"
        date_str = item.get("release_date") or item.get("first_air_date") or ""
        year = date_str[:4] if date_str else "N/A"
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

        if len(results) == 10:
            break

    return results


def _provider_names(region_block, keys):
    """Collect de-duplicated provider names for the given watch-provider
    keys ("flatrate", "free", "ads", "rent", "buy") from one region's
    entry in a /watch/providers response."""
    names = []

    for key in keys:
        for provider in (region_block or {}).get(key, []) or []:
            name = provider.get("provider_name")
            if name and name not in names:
                names.append(name)

    return names


def get_ott_status_tmdb(media_type, tmdb_id, region="US"):
    """Determine OTT/streaming release status for a title via TMDb's
    /movie/{id}/watch/providers or /tv/{id}/watch/providers endpoint.

    Preference order:
      1. Subscription streaming ("flatrate"/"free"/"ads") in `region`
         -> "✅ Streaming on: Netflix, Prime Video (US)"
      2. Rent/buy only in `region`
         -> "🛒 Available to rent/buy on: ... (US)"
      3. No data for `region` but present in some other region
         -> "🌍 Available on OTT in select regions."
      4. No watch-provider data anywhere
         -> "Not available on OTT yet."

    Never raises - any request failure returns a friendly fallback string
    so a details page can always be shown even if this lookup fails.
    """
    endpoint = "tv" if media_type == "tv" else "movie"

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}/{tmdb_id}/watch/providers",
            params={"api_key": TMDB_API_KEY},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return "⚠️ Could not check OTT availability right now."

    all_regions = data.get("results") or {}
    region_data = all_regions.get(region)

    if region_data:
        streaming = _provider_names(region_data, ("flatrate", "free", "ads"))
        if streaming:
            return f"✅ Streaming on: {', '.join(streaming)} ({region})"

        rent_buy = _provider_names(region_data, ("rent", "buy"))
        if rent_buy:
            return f"🛒 Available to rent/buy on: {', '.join(rent_buy)} ({region})"

    if all_regions:
        return "🌍 Available on OTT in select regions."

    return "Not available on OTT yet."


def get_ott_status_from_key(key_id):
    """Same as get_ott_status_tmdb(), but takes a "tmdb_movie_<id>" /
    "tmdb_tv_<id>" key (as produced by get_trending_tmdb() /
    search_titles_tmdb()) instead of separate media_type/tmdb_id args."""
    try:
        _, media_type, tmdb_id = key_id.split("_", 2)
    except ValueError:
        return "Not available on OTT yet."

    return get_ott_status_tmdb(media_type, tmdb_id)


# ---------------------------------------------------------------------------
# 📺 OTT Release This Week - English branch (see services/ott_releases.py,
# which merges this with the scraped regional-language lists, and
# keyboards/upcoming.py + plugins/callback.py for the bot-facing side)
# ---------------------------------------------------------------------------


def get_weekly_english_releases(region="US"):
    """Weekly English-language OTT release list, via TMDb's discover/movie
    with the Digital release-type filter (with_release_type=4) - confirmed
    dense and reliable for English/US, unlike this exact same filter's very
    sparse results for Indian regional languages (see chat history).

    Normalized to the same shape services.ott_releases.py's scraped
    regional entries use (title, release_date, platform, genre), plus a
    ready-to-use "key_id" ("tmdb_movie_<id>") so tapping one of these in
    the bot goes straight to the existing rich details page
    (plugins/details.py's send_trending_details()) with no extra lookup
    needed - unlike scraped regional entries, whose key_id is only
    resolved lazily if/when a user taps into one (see
    services/ott_releases.py's resolve_release_key()).

    Meant to be called once a day by services.ott_releases.py's cache, not
    per user request. Returns [] on any failure.
    """
    today = date.today()
    next_week = today + timedelta(days=7)

    try:
        response = requests.get(
            f"{BASE_URL}/discover/movie",
            params={
                "api_key": TMDB_API_KEY,
                "region": region,
                "with_release_type": 4,
                "release_date.gte": str(today),
                "release_date.lte": str(next_week),
                "with_original_language": "en",
                "sort_by": "popularity.desc",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    results = []

    for item in data.get("results", [])[:10]:
        tmdb_id = item.get("id")
        title = item.get("title") or "Unknown"
        release_date = item.get("release_date") or "N/A"
        key_id = f"tmdb_movie_{tmdb_id}"

        # One extra call per title, but this only runs during the once-a-day
        # cache refresh (services/ott_releases.py), not per user request -
        # negligible cost either way.
        platform = get_ott_status_tmdb("movie", tmdb_id, region=region)

        results.append(
            {
                "title": title,
                "release_date": release_date,
                "platform": platform,
                "genre": None,
                "language": "English",
                "key_id": key_id,
            }
        )

    return results


# ---------------------------------------------------------------------------
# 🎲 Suggest Random Movie (see keyboards/home.py + plugins/callback.py)
# ---------------------------------------------------------------------------


def get_random_movie(min_rating=7.0, min_votes=500):
    """Pick a genuinely random movie from TMDb's own quality filter -
    vote_average >= min_rating AND vote_count >= min_votes (the vote-count
    floor matters: without it, sorting/filtering purely on rating surfaces
    obscure titles with 2-3 votes at a perfect score, not genuinely
    well-regarded movies).

    Mechanism: /discover/movie with those two filters returns a paginated
    result set (up to TMDb's hard cap of 500 pages). This makes one call
    to see how many pages exist, picks a genuinely random page number, then
    makes a second call for that page and picks a random title from it -
    so repeated taps give varied results instead of always the same
    "page 1, item 1" answer sort_by would otherwise pin down.

    Returns a "tmdb_movie_<id>" key (ready for plugins/details.py's
    send_trending_details()), or None on any failure / empty result set.

    ⚠️ Kept for backward compatibility - the "🎲 Suggest Random Movie"
    button itself no longer calls this directly (it now goes through the
    language page - see get_random_movies_by_language() /
    get_random_movies_other_languages() below and
    keyboards/random_movies.py + plugins/callback.py).
    """
    base_params = {
        "api_key": TMDB_API_KEY,
        "vote_average.gte": min_rating,
        "vote_count.gte": min_votes,
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }

    try:
        first_response = requests.get(
            f"{BASE_URL}/discover/movie",
            params={**base_params, "page": 1},
            timeout=10,
        )
        first_response.raise_for_status()
        first_data = first_response.json()
    except Exception:
        return None

    total_pages = first_data.get("total_pages") or 0
    total_pages = min(total_pages, 500)  # TMDb's hard cap regardless of actual result count

    if total_pages < 1:
        return None

    random_page = random.randint(1, total_pages)

    if random_page == 1:
        page_data = first_data
    else:
        try:
            response = requests.get(
                f"{BASE_URL}/discover/movie",
                params={**base_params, "page": random_page},
                timeout=10,
            )
            response.raise_for_status()
            page_data = response.json()
        except Exception:
            page_data = first_data  # fall back to page 1's results rather than failing outright

    results = page_data.get("results") or []
    if not results:
        return None

    chosen = random.choice(results)
    tmdb_id = chosen.get("id")

    if not tmdb_id:
        return None

    return f"tmdb_movie_{tmdb_id}"


def _discover_random_page(base_params):
    """Shared helper for the language-based random-movie pickers below.

    Calls /discover/movie with `base_params` + page 1 to find out how many
    pages of results exist, then (if there's more than one) fetches one
    additional genuinely random page. Returns the combined list of raw
    TMDb result dicts from whichever page(s) were fetched - callers do
    their own shaping/filtering/sampling on top of this.

    Returns [] on any request failure or an empty result set.
    """
    try:
        first_response = requests.get(
            f"{BASE_URL}/discover/movie",
            params={**base_params, "page": 1},
            timeout=10,
        )
        first_response.raise_for_status()
        first_data = first_response.json()
    except Exception:
        return []

    total_pages = first_data.get("total_pages") or 0
    total_pages = min(total_pages, 500)  # TMDb's hard cap regardless of actual result count

    if total_pages < 1:
        return []

    results = list(first_data.get("results") or [])

    if total_pages > 1:
        random_page = random.randint(1, total_pages)
        if random_page != 1:
            try:
                response = requests.get(
                    f"{BASE_URL}/discover/movie",
                    params={**base_params, "page": random_page},
                    timeout=10,
                )
                response.raise_for_status()
                page_data = response.json()
                results.extend(page_data.get("results") or [])
            except Exception:
                pass  # fall back to just page 1's results

    return results


def _shape_discover_result(item):
    """Normalize one raw /discover/movie result dict to the same shape used
    everywhere else in this module (Title, Year, imdbID, Type, Poster) -
    see search_titles_tmdb() / get_trending_tmdb() above."""
    tmdb_id = item.get("id")
    if not tmdb_id:
        return None

    title = item.get("title") or "Unknown"
    date_str = item.get("release_date") or ""
    year = date_str[:4] if date_str else "N/A"
    poster = _poster_url(item.get("poster_path"))

    return {
        "Title": title,
        "Year": year,
        "imdbID": f"tmdb_movie_{tmdb_id}",
        "Type": "movie",
        "Poster": poster,
    }


def get_random_movies_by_language(lang_code, min_rating=7.0, min_votes=100, count=10):
    """🎲 Suggest Random Movie - language branch (Malayalam/Tamil/Hindi/
    Kannada/Telugu use min_votes=100, English/Korean use min_votes=500 -
    the actual thresholds are chosen by the caller, see
    keyboards/random_movies.py's LANGUAGE_FILTERS and
    plugins/callback.py).

    Fetches movies via /discover/movie filtered to `lang_code` (TMDb's
    with_original_language, e.g. "ml", "ta", "hi", "kn", "te", "en", "ko")
    with vote_average >= min_rating AND vote_count >= min_votes, pulls a
    genuinely random page in addition to page 1 (see
    _discover_random_page()), then returns up to `count` titles sampled
    randomly from the combined pool - so repeated taps for the same
    language give varied results.

    Returns a list of dicts shaped like get_trending_tmdb()'s results
    (Title, Year, imdbID, Type, Poster) - possibly fewer than `count` if
    the pool doesn't have that many, or [] on failure / no matches.
    """
    base_params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": lang_code,
        "vote_average.gte": min_rating,
        "vote_count.gte": min_votes,
        "sort_by": "vote_count.desc",
        "include_adult": "false",
    }

    raw_results = _discover_random_page(base_params)
    if not raw_results:
        return []

    # De-duplicate (page 1 + a second random page can overlap) while
    # keeping order, then shape and sample.
    seen_ids = set()
    unique_raw = []
    for item in raw_results:
        tmdb_id = item.get("id")
        if tmdb_id and tmdb_id not in seen_ids:
            seen_ids.add(tmdb_id)
            unique_raw.append(item)

    sample_size = min(count, len(unique_raw))
    sampled = random.sample(unique_raw, sample_size)

    shaped = [_shape_discover_result(item) for item in sampled]
    return [item for item in shaped if item]


def get_random_movies_other_languages(min_rating=7.0, min_votes=1000, count=10, exclude_codes=None):
    """🎲 Suggest Random Movie - "Others" branch: any language that ISN'T
    Malayalam/Tamil/Hindi/Kannada/Telugu/English/Korean.

    TMDb's /discover/movie only supports filtering TO one
    with_original_language at a time, not excluding a set of them, so this
    fetches a random page of the highest-quality movies overall
    (vote_average >= min_rating AND vote_count >= min_votes, sorted by
    vote count) and filters out any title whose original_language is in
    `exclude_codes` client-side. If a fetched page happens to be entirely
    excluded-language titles, this retries a few more random pages before
    giving up.

    Returns a list of dicts shaped like get_trending_tmdb()'s results
    (Title, Year, imdbID, Type, Poster) - up to `count` items, or [] on
    failure / no matches after retrying.
    """
    exclude_codes = set(exclude_codes or ())

    base_params = {
        "api_key": TMDB_API_KEY,
        "vote_average.gte": min_rating,
        "vote_count.gte": min_votes,
        "sort_by": "vote_count.desc",
        "include_adult": "false",
    }

    seen_ids = set()
    filtered_raw = []

    # A handful of tries - each pulls page 1 + one random page - is enough
    # in practice to collect `count` non-excluded titles, since the
    # overall (unfiltered) pool is dominated by English-language results
    # only at the very top of a popularity sort; sorting by vote_count
    # still surfaces plenty of other languages further down.
    for _ in range(5):
        raw_results = _discover_random_page(base_params)

        for item in raw_results:
            tmdb_id = item.get("id")
            if not tmdb_id or tmdb_id in seen_ids:
                continue
            if item.get("original_language") in exclude_codes:
                continue
            seen_ids.add(tmdb_id)
            filtered_raw.append(item)

        if len(filtered_raw) >= count:
            break

    if not filtered_raw:
        return []

    sample_size = min(count, len(filtered_raw))
    sampled = random.sample(filtered_raw, sample_size)

    shaped = [_shape_discover_result(item) for item in sampled]
    return [item for item in shaped if item]
