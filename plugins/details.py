# ✅ NEW: IMDb API lookup + formatter, used by Find Movies / Watchlist /
# Suggest Me (Feature 1, 2 & 3)
from services.imdb import get_details, get_series_episode_count, find_imdb_id_by_title_year
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

    The "✅ Done" button (callback_data "done") is shown for every
    context. Tapping it only dismisses/clears that details message; it
    never touches the saved watchlist entry itself.

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
# ✅ CHANGED: "Suggest Me" details page (Feature 2)
#
# TMDB (services/tmdb.py) is used ONLY to build/sort the "Suggest Me"
# recommendation list itself. Once the user taps one of the suggested
# titles, this now resolves that title on the free IMDb API (by title +
# year, via services.imdb.find_imdb_id_by_title_year()) instead of making
# a second TMDB lookup - so the details page it opens is sourced from
# IMDb exactly like every other details page in the bot (Find Movies &
# Series, Watchlist), and shows the same full set of fields.
# ---------------------------------------------------------------------------

async def send_suggested_details(client, chat_id, title, year, media_type, user_id=None):
    """Show the details page for a title picked from the "Suggest Me"
    recommendation list.

    `title`/`year` come from the cached TMDB discover result the user
    tapped (plugins/callback.py pulls them from database.user_state's
    saved results by TMDB id) - `media_type` is only used for the "not
    found" error message, since get_details() below determines the real
    Movie/Series type itself from the IMDb API.
    """
    imdb_id = find_imdb_id_by_title_year(title, year)

    if not imdb_id:
        label = "Series" if media_type == "series" else "Movie"
        await client.send_message(chat_id, f"❌ Could not find details for this {label.lower()}.")
        return

    await send_imdb_details(client, chat_id, imdb_id, user_id=user_id, context="search")
