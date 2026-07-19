# ---------------------------------------------------------------------------
# ✅ NEW (Feature 6): Display labels for the raw genre/language values kept
# in user_state (database/user_state.py) - callback_data uses short slugs
# like "scifi"/"tvmovie" (keyboards/genre.py) and ISO codes like "ta"/"ja"
# (keyboards/language.py), which aren't fit to show to the user directly.
# Used only by format_movies() below to print what was actually selected
# at the top of a "Suggest Me" results list.
# ---------------------------------------------------------------------------

GENRE_LABELS = {
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "comedy": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "history": "History",
    "horror": "Horror",
    "music": "Music",
    "mystery": "Mystery",
    "romance": "Romance",
    "scifi": "Sci-Fi",
    "tvmovie": "TV Movie",
    "thriller": "Thriller",
    "war": "War",
    "western": "Western",
}

LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "ml": "Malayalam",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "de": "German",
    "ru": "Russian",
}


def format_movies(results, genre=None, language=None, rating=None):
    """Format the top 10 movie/series recommendations.
    Handles both movies and TV series.

    ✅ NEW (Feature 6): `genre`, `language`, and `rating` are the raw values
    saved in user_state during the "Suggest Me" flow (plugins/movie.py /
    plugins/series.py pass state.get("genre"/"language"/"rating") straight
    through). When given, a summary line showing what was selected is
    printed under the header, above the numbered list.
    """

    if not results:
        return "❌ No movies found matching your selection."

    # ✅ Check if results are movies or series
    is_series = "name" in results[0] if results else False

    if is_series:
        text = (
            "📺 **Top 10 Recommended Series**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        text = (
            "🎬 **Top 10 Recommended Movies**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

    # ✅ NEW: Selected Genre / Language / IMDb Rating summary line.
    genre_label = GENRE_LABELS.get(genre, genre.title() if genre else None)
    language_label = LANGUAGE_LABELS.get(language, language.upper() if language else None)
    # `rating` is stored with a +0.01 offset (e.g. 6.01 for "6+", see the
    # "rating_" handler in plugins/callback.py) so int() below recovers the
    # original selected value (6) to display as "6+".
    rating_label = f"{int(rating)}+" if isinstance(rating, (int, float)) else None

    if genre_label or language_label or rating_label:
        if genre_label:
            text += f"🎭 Genre : **{genre_label}**\n"
        if language_label:
            text += f"🌍 Language : **{language_label}**\n"
        if rating_label:
            text += f"⭐ Minimum IMDb Rating : **{rating_label}**\n"
        text += "\n"

    for index, item in enumerate(results[:10], start=1):
        if is_series:
            # ✅ Handle TV Series correctly
            title = item.get("name", "Unknown")  # ✅ Use "name" for series
            release_date = item.get("first_air_date", "")  # ✅ Use "first_air_date"
            year = release_date[:4] if release_date else "----"
            rating_value = item.get("vote_average", "N/A")
        else:
            # Handle Movies
            title = item.get("title", "Unknown")
            release_date = item.get("release_date", "")
            year = release_date[:4] if release_date else "----"
            rating_value = item.get("vote_average", "N/A")

        text += (
            f"**{index}. {title} ({year})**\n"
            f"⭐ Rating: **{rating_value}**\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━"
    return text


# ---------------------------------------------------------------------------
# ✅ NEW: IMDb-based details formatter (Feature 2 - Movie Details Page)
# ---------------------------------------------------------------------------

def _clean(value):
    """The IMDb API (services/imdb.py) leaves unavailable fields as None
    (older data sometimes used the literal string 'N/A') - treat both the
    same so callers can skip that line entirely."""
    if not value or value == "N/A":
        return None
    return value


def format_imdb_details(details, total_episodes=None):
    """Build a rich caption for a movie/series using IMDb API data
    (services/imdb.py's get_details()).

    Covers: Title, Release Year, Runtime, Genres, IMDb Rating, Vote Count,
    Content Rating, Language, Country, Director, Writers, Cast, Plot, Awards -
    any field the API didn't have for this title is simply omitted.

    ✅ NEW (Feature 1): For a series, also shows the number of Seasons
    (from the IMDb API's "totalSeasons" field) and the total number of Episodes.

    `total_episodes` is computed separately via
    services.imdb.get_series_episode_count(), since the IMDb API doesn't return it
    directly - pass None to omit the Episodes line (e.g. it couldn't be
    determined). This is used everywhere a title's details are shown -
    Find Movies & Series, Watchlist, and Suggest Me - so all three stay
    identical (Feature 2).
    """
    title = details.get("Title", "Unknown")
    year = details.get("Year", "-")
    media_type = details.get("Type", "movie")

    runtime = _clean(details.get("Runtime"))
    genre = _clean(details.get("Genre"))
    total_seasons = _clean(details.get("totalSeasons"))
    imdb_rating = _clean(details.get("imdbRating"))
    imdb_votes = _clean(details.get("imdbVotes"))
    rated = _clean(details.get("Rated"))
    language = _clean(details.get("Language"))
    country = _clean(details.get("Country"))
    director = _clean(details.get("Director"))
    writer = _clean(details.get("Writer"))
    actors = _clean(details.get("Actors"))
    awards = _clean(details.get("Awards"))
    plot = _clean(details.get("Plot")) or "No plot summary available."

    icon = "📺" if media_type == "series" else "🎬"

    caption = f"{icon} **{title} ({year})**\n\n"

    if runtime:
        caption += f"⏱ Runtime : {runtime}\n"
    if genre:
        caption += f"🎭 Genres : {genre}\n"
    if media_type == "series":
        if total_seasons:
            caption += f"📊 Seasons : {total_seasons}\n"
        if total_episodes:
            caption += f"📺 Episodes : {total_episodes}\n"
    if imdb_rating:
        caption += f"⭐ IMDb Rating : {imdb_rating}/10\n"
    if imdb_votes:
        caption += f"🗳 Vote Count : {imdb_votes}\n"
    if rated:
        caption += f"🔞 Content Rating : {rated}\n"
    if language:
        caption += f"🗣 Language : {language}\n"
    if country:
        caption += f"🌍 Country : {country}\n"
    if director:
        caption += f"🎬 Director : {director}\n"
    if writer:
        caption += f"✍️ Writers : {writer}\n"
    if actors:
        caption += f"🎟 Cast : {actors}\n"
    if awards:
        caption += f"🏆 Awards : {awards}\n"

    caption += f"\n📝 {plot}"

    return caption
