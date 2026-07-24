# ---------------------------------------------------------------------------
# Details-page formatter, shared by both search flows
# (SEARCH - IMDb / SEARCH - TMDb) and the Watchlist.
# ---------------------------------------------------------------------------


def _clean(value):
    """Both services/imdb.py and services/tmdb.py leave unavailable fields
    as the literal string "N/A" - treat that the same as missing so callers
    can skip that line entirely."""
    if not value or value == "N/A":
        return None
    return value


def format_imdb_details(details, total_episodes=None):
    """Build a rich caption for a movie/series using the normalized details
    dict produced by services.imdb.get_details() or
    services.tmdb.get_details_tmdb() (plugins/details.py's fetch_details()
    picks whichever one applies).

    Covers: Title, Release Year, Runtime, Genres, Rating, Vote Count,
    Content Rating, Language, Country, Director, Writers, Cast, Plot,
    Awards - any field the source didn't have for this title is simply
    omitted.

    ✅ The rating line's label follows details["Source"] ("imdb" or
    "tmdb", set by whichever service built this dict) - "⭐ IMDb Rating"
    for a SEARCH - IMDb result, "⭐ TMDb Rating" for a SEARCH - TMDb result,
    since the number itself comes from that source's own rating, not
    IMDb's, when found via TMDb.

    For a series, also shows the number of Seasons (from the "totalSeasons"
    field) and the total number of Episodes.

    `total_episodes` is computed separately by the caller (source-specific -
    see plugins/details.py's _total_episodes()) since it isn't always part
    of `details` itself - pass None to omit the Episodes line. This is used
    everywhere a title's details are shown (both search flows and the
    Watchlist), so all of them stay identical.
    """
    title = details.get("Title", "Unknown")
    year = details.get("Year", "-")
    media_type = details.get("Type", "movie")
    source = details.get("Source", "imdb")

    runtime = _clean(details.get("Runtime"))
    genre = _clean(details.get("Genre"))
    total_seasons = _clean(details.get("totalSeasons"))
    rating = _clean(details.get("imdbRating"))
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
    rating_label = "TMDb Rating" if source == "tmdb" else "IMDb Rating"

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
    if rating:
        caption += f"⭐ {rating_label} : {rating}/10\n"
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
