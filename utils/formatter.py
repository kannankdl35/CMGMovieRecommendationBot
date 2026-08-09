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


def format_imdb_details(details, total_episodes=None, enabled_fields=None):
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

    ✅ NEW - ⚙️ Settings feature: `enabled_fields` is the per-user field
    visibility dict built by database/settings_db.py's get_settings() (see
    plugins/details.py, which looks it up - keyed by details["Source"] -
    before calling this function). Any field whose key resolves to False
    is left out of the caption entirely, same as if the source itself
    never had that field. Passing None (the default) shows every field
    exactly as before this feature existed - only plugins/details.py's
    three callers ever pass an explicit dict.
    """

    def enabled(key):
        if enabled_fields is None:
            return True
        return enabled_fields.get(key, True)

    title = details.get("Title", "Unknown")
    year = details.get("Year", "-")
    media_type = details.get("Type", "movie")
    source = details.get("Source", "imdb")

    runtime = _clean(details.get("Runtime")) if enabled("runtime") else None
    genre = _clean(details.get("Genre")) if enabled("genres") else None
    total_seasons = _clean(details.get("totalSeasons")) if enabled("seasons") else None
    rating = _clean(details.get("imdbRating")) if enabled("rating") else None
    imdb_votes = _clean(details.get("imdbVotes"))
    rated = _clean(details.get("Rated"))
    language = _clean(details.get("Language")) if enabled("language") else None
    country = _clean(details.get("Country")) if enabled("country") else None
    director = _clean(details.get("Director")) if enabled("director") else None
    writer = _clean(details.get("Writer")) if enabled("writers") else None
    actors = _clean(details.get("Actors")) if enabled("cast") else None
    awards = _clean(details.get("Awards"))
    plot = _clean(details.get("Plot")) if enabled("plot") else None
    if enabled("plot") and not plot:
        plot = "No plot summary available."

    icon = "📺" if media_type == "series" else "🎬"
    rating_label = "TMDb Rating" if source == "tmdb" else "IMDb Rating"

    # ✅ NEW - Title/Year are themselves toggleable fields (see
    # database/settings_db.py's IMDB_FIELD_ORDER/TMDB_FIELD_ORDER) - build
    # the header out of whichever of the two are enabled, falling back to
    # just the movie/series icon if both are hidden.
    header_parts = []
    if enabled("title"):
        header_parts.append(title)
    if enabled("year"):
        header_parts.append(f"({year})")
    header = " ".join(header_parts).strip()

    caption = f"{icon} **{header}**\n\n" if header else f"{icon}\n\n"

    if runtime:
        caption += f"⏱ Runtime : {runtime}\n"
    if genre:
        caption += f"🎭 Genres : {genre}\n"
    if media_type == "series":
        if total_seasons:
            caption += f"📊 Seasons : {total_seasons}\n"
        if total_episodes and enabled("episodes"):
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

    if plot:
        caption += f"\n📝 {plot}"

    return caption


# ---------------------------------------------------------------------------
# ✅ NEW - ✏️ Custom Caption feature (see database/settings_db.py's
# get_custom_caption()/set_custom_caption(), plugins/custom_caption.py's
# "✏️ Custom Caption" page under IMDb/TMDb Settings, and
# plugins/details.py, which picks render_custom_caption() below instead
# of format_imdb_details() above whenever a user has saved a template.)
#
# Every #TAG a saved template can use, per source - kept in the same
# order they're shown to the user (plugins/custom_caption.py's
# "Available tags" list), and matching database/settings_db.py's
# IMDB_FIELD_ORDER / TMDB_FIELD_ORDER minus "poster" (the poster is
# always sent as the photo/attachment itself, never part of the caption
# text - see plugins/details.py's _resolve_display()).
# ---------------------------------------------------------------------------
IMDB_CAPTION_TAGS = [
    "TITLE", "YEAR", "RUNTIME", "GENRES", "RATING",
    "DIRECTOR", "WRITERS", "CAST", "PLOT",
]

TMDB_CAPTION_TAGS = [
    "TITLE", "YEAR", "RUNTIME", "GENRES", "SEASONS", "EPISODES",
    "RATING", "LANGUAGE", "COUNTRY", "DIRECTOR", "WRITERS", "CAST", "PLOT",
]


def caption_tags_for(source):
    return TMDB_CAPTION_TAGS if source == "tmdb" else IMDB_CAPTION_TAGS


def _caption_tag_values(details, total_episodes=None):
    """Build the #TAG -> plain-text value mapping used by
    render_custom_caption() below. Same underlying fields as
    format_imdb_details() above, just exposed as raw substitution values
    instead of pre-built, labelled caption lines - a field this
    title/source doesn't actually have (e.g. #LANGUAGE for an IMDb
    result, which never has one) resolves to an empty string rather than
    "N/A", so a template that includes it just leaves that spot blank
    instead of showing a literal "N/A".
    """
    plot = _clean(details.get("Plot")) or "No plot summary available."

    return {
        "TITLE": details.get("Title") or "",
        "YEAR": _clean(details.get("Year")) or "",
        "RUNTIME": _clean(details.get("Runtime")) or "",
        "GENRES": _clean(details.get("Genre")) or "",
        "SEASONS": _clean(details.get("totalSeasons")) or "",
        "EPISODES": str(total_episodes) if total_episodes else "",
        "RATING": _clean(details.get("imdbRating")) or "",
        "LANGUAGE": _clean(details.get("Language")) or "",
        "COUNTRY": _clean(details.get("Country")) or "",
        "DIRECTOR": _clean(details.get("Director")) or "",
        "WRITERS": _clean(details.get("Writer")) or "",
        "CAST": _clean(details.get("Actors")) or "",
        "PLOT": plot,
    }


def render_custom_caption(template, details, total_episodes=None):
    """✅ NEW - ✏️ Custom Caption feature: fill in a user's saved caption
    template with this title's real details, replacing every #TAG it
    contains (see caption_tags_for() above for the supported list per
    source) with the matching plain-text value - any of the user's own
    text (channel name, emoji, formatting, ...) around/between the tags
    is left exactly as they wrote it. Used by plugins/details.py in place
    of format_imdb_details() whenever database/settings_db.py's
    get_custom_caption() finds a saved template for this user/source -
    the per-field ✅/❌ toggles (⚙️ Settings) have no effect on a custom
    caption's text body; the template itself is now the user's full
    choice of what appears there (the Poster toggle still applies
    separately, since it controls whether this is sent as a photo at
    all - see plugins/details.py's _resolve_display()).
    """
    values = _caption_tag_values(details, total_episodes=total_episodes)

    caption = template
    for tag, value in values.items():
        caption = caption.replace(f"#{tag}", value)

    return caption
