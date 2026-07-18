# ✅ Import series_details as well
from services.details import movie_details, series_details

# ✅ NEW: OMDb-based lookup + formatter, used by Find Movies / Watchlist /
# Suggest Me (Feature 1, 2 & 3)
from services.omdb import get_details, get_series_episode_count
from utils.formatter import format_omdb_details
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ✅ NEW: used to auto-detect whether a title is already saved, so the
# correct watchlist button (Add vs Delete) is shown regardless of where
# the details page was opened from (Feature 2 & 3 fix).
from database.watchlist_db import is_in_watchlist

IMAGE_URL = "https://image.tmdb.org/t/p/w500"


# ---------------------------------------------------------------------------
# Legacy TMDB-only caption builders.
#
# These are now only used as a last-resort fallback inside
# send_suggested_details() below, for the rare case a "Suggest Me" title
# has no IMDb ID on TMDB and the rich OMDb details page can't be built.
# Every normal details view (Find Movies & Series, Watchlist, and Suggest
# Me) renders through send_omdb_details()/format_omdb_details() instead,
# so all three show identical information (Feature 2).
# ---------------------------------------------------------------------------

def get_movie_caption(movie):
    title = movie.get("title", "Unknown")
    rating = movie.get("vote_average", "N/A")
    release = movie.get("release_date", "-")
    overview = movie.get("overview", "No overview available.")

    genres = ", ".join(
        genre["name"] for genre in movie.get("genres", [])
    )

    caption = (
        f"🎬 **{title}**\n\n"
        f"⭐ Rating : {rating}\n"
        f"📅 Release : {release}\n"
        f"🎭 Genres : {genres}\n\n"
        f"📝 {overview}"
    )

    poster = movie.get("poster_path")
    if poster:
        poster = IMAGE_URL + poster

    return poster, caption


def get_series_caption(series):
    """Format TV series details including number of seasons and episodes"""
    title = series.get("name", "Unknown")
    rating = series.get("vote_average", "N/A")
    release = series.get("first_air_date", "-")
    overview = series.get("overview", "No overview available.")

    num_seasons = series.get("number_of_seasons", "N/A")
    num_episodes = series.get("number_of_episodes", "N/A")

    genres = ", ".join(
        genre["name"] for genre in series.get("genres", [])
    )

    caption = (
        f"📺 **{title}**\n\n"
        f"⭐ Rating : {rating}\n"
        f"📅 First Air : {release}\n"
        f"🎭 Genres : {genres}\n"
        f"📊 Seasons : {num_seasons}\n"
        f"📺 Episodes : {num_episodes}\n"
        f"\n📝 {overview}"
    )

    poster = series.get("poster_path")
    if poster:
        poster = IMAGE_URL + poster

    return poster, caption


def get_movie_info(movie_id):
    movie = movie_details(movie_id)
    if not movie:
        return None, None
    return get_movie_caption(movie)


def get_series_info(series_id):
    """Fetch and format TV series information"""
    series = series_details(series_id)
    if not series:
        return None, None
    return get_series_caption(series)


# ---------------------------------------------------------------------------
# ✅ Feature 1, 2, 3 & 4 - Rich OMDb details page + Trailer / Watchlist /
# Done buttons. Used by "Find Movies & Series" search results, the
# "/watchlist" listing, AND "Suggest Me" (via send_suggested_details below),
# so all three show identical information and controls.
# ---------------------------------------------------------------------------

def build_details_keyboard(imdb_id, in_watchlist, context="search"):
    """Build the Trailer / Watchlist (Add or Delete) / Done inline keyboard
    shown under a details page.

    `context` controls how the Watchlist button behaves once tapped, and
    whether a Done button is shown at all:

    - "search" (default): used for "Find Movies & Series" results and
      "Suggest Me" results.
        * Add to Watchlist  -> callback_data "addwl_<imdb_id>"
        * Delete from Watchlist -> callback_data "rmwl_<imdb_id>": removes
          the item from the database, shows a popup confirmation, and
          swaps the button back to "Add to Watchlist" IN PLACE - the
          message itself is never deleted.
        * A "✅ Done" button (callback_data "done") is shown so the user
          can dismiss the details message when finished with it.
    - "watchlist": used for details opened from the user's own
      /watchlist listing (unchanged behavior).
        * Delete from Watchlist -> callback_data "delwl_<imdb_id>":
          removes the item, deletes this details message, and refreshes
          the watchlist listing.
        * No Done button (not requested for this flow).

    All of these callback_data values are handled in plugins/callback.py.
    """
    if in_watchlist:
        if context == "watchlist":
            watchlist_button = InlineKeyboardButton(
                "🗑 Delete from Watchlist", callback_data=f"delwl_{imdb_id}"
            )
        else:
            watchlist_button = InlineKeyboardButton(
                "🗑 Delete from Watchlist", callback_data=f"rmwl_{imdb_id}"
            )
    else:
        watchlist_button = InlineKeyboardButton(
            "❤️ Add to Watchlist", callback_data=f"addwl_{imdb_id}"
        )

    rows = [
        [InlineKeyboardButton("🎬 Trailer", callback_data=f"trailer_{imdb_id}")],
        [watchlist_button],
    ]

    if context == "search":
        rows.append([InlineKeyboardButton("✅ Done", callback_data="done")])

    return InlineKeyboardMarkup(rows)


async def send_omdb_details(client, chat_id, imdb_id, user_id=None, in_watchlist=None, context="search"):
    """Fetch full OMDb details for imdb_id and send a rich details message
    with Poster, full info caption, and Trailer / Watchlist / Done buttons.

    ✅ For a series, the caption now also includes the number of Seasons
    and total Episodes (Feature 1), computed via
    services.omdb.get_series_episode_count().

    `in_watchlist` controls which watchlist button is shown:
    - None (default): auto-detect by checking the database for `user_id`
      (Feature 2 & 3 fix) - this makes the button correct no matter where
      the details page was opened from, instead of trusting the caller
      to know.
    - True/False: explicit override, used by callers that already know
      the answer (e.g. the Watchlist listing itself).

    `context` is passed straight through to build_details_keyboard() -
    see that function for what "search" vs "watchlist" changes.
    """
    details = get_details(imdb_id)

    if not details:
        await client.send_message(chat_id, "❌ Could not find details for this title.")
        return

    total_episodes = None
    if details.get("Type") == "series":
        total_episodes = get_series_episode_count(imdb_id, details.get("totalSeasons"))

    caption = format_omdb_details(details, total_episodes=total_episodes)

    poster = details.get("Poster")
    poster = poster if poster and poster != "N/A" else None

    if in_watchlist is None:
        # Auto-detect - falls back to False (Add) if we have no user_id to check.
        in_watchlist = await is_in_watchlist(user_id, imdb_id) if user_id else False

    buttons = build_details_keyboard(imdb_id, in_watchlist, context=context)

    try:
        if poster:
            await client.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=caption,
                reply_markup=buttons
            )
        else:
            await client.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=buttons
            )
    except Exception:
        # ✅ Fallback to text if the poster URL fails to load as a photo
        await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=buttons
        )


# ---------------------------------------------------------------------------
# ✅ NEW: "Suggest Me" details page (Feature 2)
# ---------------------------------------------------------------------------

async def send_suggested_details(client, chat_id, tmdb_id, media_type, user_id=None):
    """Show the details page for a title picked from the "Suggest Me"
    recommendation list.

    Looks the TMDB item up first to get its IMDb ID, then delegates to
    send_omdb_details() so "Suggest Me" renders the exact same details
    page (info + Trailer / Watchlist / Done buttons) as "Find Movies &
    Series" (Feature 2 & 3).

    Falls back to the old bare TMDB-only caption (no buttons) only in the
    rare case TMDB doesn't have an IMDb ID on file for this title - the
    Watchlist is keyed by IMDb ID, so Add to Watchlist isn't possible
    without one.
    """
    if media_type == "series":
        data = series_details(tmdb_id)
        imdb_id = (data or {}).get("external_ids", {}).get("imdb_id")
    else:
        data = movie_details(tmdb_id)
        imdb_id = (data or {}).get("imdb_id")

    if not data:
        error_msg = "Series not found." if media_type == "series" else "Movie not found."
        await client.send_message(chat_id, f"❌ {error_msg}")
        return

    if imdb_id:
        await send_omdb_details(client, chat_id, imdb_id, user_id=user_id, context="search")
        return

    # Fallback: no IMDb ID available from TMDB.
    if media_type == "series":
        poster, caption = get_series_caption(data)
    else:
        poster, caption = get_movie_caption(data)

    if poster:
        await client.send_photo(chat_id=chat_id, photo=poster, caption=caption)
    else:
        await client.send_message(chat_id=chat_id, text=caption)
