def format_movies(results):
    """Format the top 10 movie/series recommendations.
    Handles both movies and TV series."""

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

    for index, item in enumerate(results[:10], start=1):
        if is_series:
            # ✅ Handle TV Series correctly
            title = item.get("name", "Unknown")  # ✅ Use "name" for series
            release_date = item.get("first_air_date", "")  # ✅ Use "first_air_date"
            year = release_date[:4] if release_date else "----"
            rating = item.get("vote_average", "N/A")
        else:
            # Handle Movies
            title = item.get("title", "Unknown")
            release_date = item.get("release_date", "")
            year = release_date[:4] if release_date else "----"
            rating = item.get("vote_average", "N/A")

        text += (
            f"**{index}. {title} ({year})**\n"
            f"⭐ Rating: **{rating}**\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━"
    return text


# ---------------------------------------------------------------------------
# ✅ NEW: OMDb-based details formatter (Feature 2 - Movie Details Page)
# ---------------------------------------------------------------------------

def _clean(value):
    """OMDb uses the literal string 'N/A' for missing fields.
    Return None so callers can skip that line entirely."""
    if not value or value == "N/A":
        return None
    return value


def format_omdb_details(details):
    """Build a rich caption for a movie/series using OMDb API data.

    Covers: Title, Release Year, Runtime, Genres, IMDb Rating, Vote Count,
    Content Rating, Language, Country, Director, Writers, Cast, Plot, Awards.
    """
    title = details.get("Title", "Unknown")
    year = details.get("Year", "-")
    media_type = details.get("Type", "movie")

    runtime = _clean(details.get("Runtime"))
    genre = _clean(details.get("Genre"))
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
