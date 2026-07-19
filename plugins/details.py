# ✅ Import series_details as well
from services.details import movie_details, series_details

# ✅ NEW: IMDb API lookup + formatter, used by Find Movies / Watchlist /
# Suggest Me (Feature 1, 2 & 3)
from services.imdb import get_details, get_series_episode_count
from utils.formatter import format_imdb_details
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ✅ NEW (Feature 6): used to embed a real Trailer URL button directly on
# details pages opened from an inline search result - those messages have
# no chat/message object to reply into (only an inline_message_id), so the
# lazy "tap Trailer to fetch it" callback used elsewhere doesn't work there;
# the trailer link has to be fetched up front and attached as a URL button.
from services.youtube import get_trailer_url

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
# has no IMDb ID on TMDB and the rich IMDb details page can't be built.
# Every normal details view (Find Movies & Series, Watchlist, and Suggest
# Me) renders through send_imdb_details()/format_imdb_details() instead,
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
# ✅ Feature 1, 2, 3 & 4 - Rich IMDb details page + Trailer / Watchlist /
# Done buttons. Used by "Find Movies & Series" search results, the
# "/watchlist" listing, AND "Suggest Me" (via send_suggested_details below),
# so all three show identical information and controls.
# ---------------------------------------------------------------------------

def build_details_keyboard(imdb_id, in_watchlist, context="search", trailer_url=None):
    """Build the Trailer / Watchlist (Add or Delete) / Done inline keyboard
    shown under a details page.

    `context` controls how the Watchlist button behaves once tapped, and
    which details page this keyboard belongs to:

    - "search" (default): used for "Find Movies & Series" results and
      "Suggest Me" results.
        * Add to Watchlist  -> callback_data "addwl_<imdb_id>"
        * Delete from Watchlist -> callback_data "rmwl_<imdb_id>": removes
          the item from the database, shows a popup confirmation, and
          swaps the button back to "Add to Watchlist" IN PLACE - the
          message itself is never deleted.
    - "watchlist": used for details opened from the user's own
      /watchlist listing.
        * Delete from Watchlist -> callback_data "delwl_<imdb_id>":
          removes the item, deletes this details message, and refreshes
          the watchlist listing.
    - "inline" (Feature 6, NEW): used for the full details page shown
      automatically right after a title is picked from an inline "Find
      Movies & Series" search (see plugins/inline.py's
      inline_result_chosen()). These messages only have an
      inline_message_id (no chat/message object), so:
        * the Trailer button is a plain URL button built from
          `trailer_url` (fetched up front by the caller) instead of a
          lazy callback_data lookup - it's simply omitted if no trailer
          was found.
        * Add/Delete Watchlist still use "addwl_"/"rmwl_", handled with an
          inline-safe branch in plugins/callback.py.

    ✅ CHANGED (Feature 6): the "✅ Done" button (callback_data "done") is
    now shown for every context, not just "search" - including details
    pages opened from the Watchlist and from inline search results.
    Tapping it only dismisses/clears that details message; it never
    touches the saved watchlist entry itself.

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

    rows = []

    if context == "inline":
        if trailer_url:
            rows.append([InlineKeyboardButton("🎬 Trailer", url=trailer_url)])
        # No trailer found for this title - simply omit the row rather
        # than showing a button that can't do anything.
    else:
        rows.append(
            [InlineKeyboardButton("🎬 Trailer", callback_data=f"trailer_{imdb_id}")]
        )

    rows.append([watchlist_button])
    rows.append([InlineKeyboardButton("✅ Done", callback_data="done")])

    return InlineKeyboardMarkup(rows)


async def send_imdb_details(client, chat_id, imdb_id, user_id=None, in_watchlist=None, context="search"):
    """Fetch full IMDb API details for imdb_id and send a rich details message
    with Poster, full info caption, and Trailer / Watchlist / Done buttons.

    ✅ For a series, the caption now also includes the number of Seasons
    and total Episodes (Feature 1), computed via
    services.imdb.get_series_episode_count().

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

    caption = format_imdb_details(details, total_episodes=total_episodes)

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
# ✅ NEW (Feature 6): Full details page shown right after picking a title
# from an inline "Find Movies & Series" search - no extra "View Details"
# tap needed. Called from plugins/inline.py's inline_result_chosen()
# (an @Client.on_chosen_inline_result() handler), which fires the moment
# Telegram inserts the chosen result into the chat.
#
# Unlike send_imdb_details() above, there is no chat/message object to
# send into here - Telegram only gives us the inline_message_id of the
# card it just inserted, so the existing short card is *edited in place*
# into the full details page instead of a new message being sent.
# ---------------------------------------------------------------------------

async def send_imdb_details_inline(client, inline_message_id, imdb_id, user_id=None):
    """Edit an inline-inserted search-result card into the full details
    page (poster + full info caption + Trailer/Watchlist/Done buttons),
    in place, via its inline_message_id.
    """
    details = get_details(imdb_id)

    if not details:
        try:
            await client.edit_inline_text(
                inline_message_id, "❌ Could not find details for this title."
            )
        except Exception:
            try:
                await client.edit_inline_caption(
                    inline_message_id, "❌ Could not find details for this title."
                )
            except Exception:
                pass
        return

    total_episodes = None
    if details.get("Type") == "series":
        total_episodes = get_series_episode_count(imdb_id, details.get("totalSeasons"))

    caption = format_imdb_details(details, total_episodes=total_episodes)

    # Fetched eagerly (rather than on tap) since an inline message has no
    # chat to reply a trailer link into - see build_details_keyboard()'s
    # "inline" context above.
    trailer_url = get_trailer_url(details.get("Title"), details.get("Year"))

    in_watchlist = await is_in_watchlist(user_id, imdb_id) if user_id else False

    buttons = build_details_keyboard(
        imdb_id, in_watchlist, context="inline", trailer_url=trailer_url
    )

    poster = details.get("Poster")
    poster = poster if poster and poster != "N/A" else None

    try:
        if poster:
            await client.edit_inline_caption(inline_message_id, caption, reply_markup=buttons)
        else:
            await client.edit_inline_text(inline_message_id, caption, reply_markup=buttons)
    except Exception:
        # The card started out as the other kind of message (e.g. a
        # text-only fallback card that now needs a poster, or a photo API
        # edit rejected for some reason) - fall back to a plain text edit
        # so the user still gets the full details even if the poster
        # doesn't come along.
        try:
            await client.edit_inline_text(inline_message_id, caption, reply_markup=buttons)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# ✅ NEW: "Suggest Me" details page (Feature 2)
# ---------------------------------------------------------------------------

async def send_suggested_details(client, chat_id, tmdb_id, media_type, user_id=None):
    """Show the details page for a title picked from the "Suggest Me"
    recommendation list.

    Looks the TMDB item up first to get its IMDb ID, then delegates to
    send_imdb_details() so "Suggest Me" renders the exact same details
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
        await send_imdb_details(client, chat_id, imdb_id, user_id=user_id, context="search")
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
