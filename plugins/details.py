import asyncio

# IMDb + TMDb detail lookup & formatter, used by both search flows
# (SEARCH - IMDb / SEARCH - TMDb) and by the Watchlist.
from services.imdb import get_details, get_series_episode_count
from services.tmdb import get_details_tmdb
from utils.formatter import format_imdb_details
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Used to auto-detect whether a title is already saved, so the correct
# watchlist button (Add vs Delete) is shown regardless of where the details
# page was opened from.
from database.watchlist_db import is_in_watchlist


def _source_mode(key_id):
    """"tmdb" for a TMDb-sourced key ("tmdb_movie_603" / "tmdb_tv_1396"),
    "imdb" for a real IMDb id ("tt1234567") - see services/tmdb.py."""
    return "tmdb" if key_id and key_id.startswith("tmdb_") else "imdb"


def fetch_details(key_id):
    """Resolve full details for either an IMDb id ("tt1234567", from the
    SEARCH - IMDb flow) or a TMDb-sourced key ("tmdb_movie_603" /
    "tmdb_tv_1396", from the SEARCH - TMDb flow - see services/tmdb.py).

    This is the single place that decides which backend to call - every
    other part of the bot (watchlist, add/remove buttons,
    plugins/callback.py, plugins/inline.py) just passes whichever key_id it
    was originally given straight through to this function. This makes a
    blocking HTTP request - call it via asyncio.to_thread() from async code
    (see send_imdb_details() below) rather than awaiting it directly.
    """
    if _source_mode(key_id) == "tmdb":
        return get_details_tmdb(key_id)
    return get_details(key_id)


def _total_episodes(key_id, details):
    if details.get("Type") != "series":
        return None

    if _source_mode(key_id) == "tmdb":
        # TMDb gives this directly - see services/tmdb.py's get_details_tmdb().
        return details.get("_total_episodes")

    # The IMDb API this bot uses doesn't return season/episode data at all,
    # so this always resolves to None - kept for symmetry / possible future
    # data source.
    return get_series_episode_count(key_id, details.get("totalSeasons"))


def build_details_keyboard(key_id, in_watchlist, context="search"):
    """Build the Watchlist (Add or Delete) / Search Another / Done inline
    keyboard shown under a details page.

    `context` controls how the Watchlist button behaves once tapped:

    - "search" (default): used for SEARCH - IMDb / SEARCH - TMDb results
      (including the details page shown right after picking an inline
      result - see plugins/inline.py's inline_result_chosen()).
        * Add to Watchlist  -> callback_data "addwl_<key_id>"
        * Delete from Watchlist -> callback_data "rmwl_<key_id>": removes
          the item from the database, shows a popup confirmation, and
          swaps the button back to "Add to Watchlist" IN PLACE - the
          message itself is never deleted.
    - "watchlist": used for details opened from the user's own
      /watchlist listing.
        * Delete from Watchlist -> callback_data "delwl_<key_id>":
          removes the item, deletes this details message, and refreshes
          the watchlist listing.

    "🔎 Search Another Movie/Series" pre-fills "imdb "/"tmdb " into the
    chat's inline query box (same mechanic as the Home menu's two search
    buttons, see keyboards/home.py) - always for the SAME source this
    title came from, based on whether key_id has a "tmdb_" prefix, so
    tapping it continues searching on the same site as the last result.

    The "✅ Done" button (callback_data "done") is shown for every context.
    Tapping it only dismisses/clears that details message; it never
    touches the saved watchlist entry itself.

    All of these callback_data values are handled in plugins/callback.py.
    """
    if in_watchlist:
        if context == "watchlist":
            watchlist_button = InlineKeyboardButton(
                "🗑 Delete from Watchlist", callback_data=f"delwl_{key_id}"
            )
        else:
            watchlist_button = InlineKeyboardButton(
                "🗑 Delete from Watchlist", callback_data=f"rmwl_{key_id}"
            )
    else:
        watchlist_button = InlineKeyboardButton(
            "❤️ Add to Watchlist", callback_data=f"addwl_{key_id}"
        )

    mode = _source_mode(key_id)

    rows = [
        [watchlist_button],
        [
            InlineKeyboardButton(
                "🔎 Search Another Movie/Series",
                switch_inline_query_current_chat=f"{mode} ",
            )
        ],
        [InlineKeyboardButton("✅ Done", callback_data="done")],
    ]

    return InlineKeyboardMarkup(rows)


async def send_imdb_details(client, chat_id, key_id, user_id=None, in_watchlist=None, context="search"):
    """Fetch full details for key_id and send a rich details message with
    Poster, full info caption, and Watchlist / Search Another / Done
    buttons.

    `in_watchlist` controls which watchlist button is shown:
    - None (default): auto-detect by checking the database for `user_id`
      - this makes the button correct no matter where the details page was
        opened from, instead of trusting the caller to know.
    - True/False: explicit override, used by callers that already know the
      answer (e.g. the Watchlist listing itself).

    `context` is passed straight through to build_details_keyboard() - see
    that function for what "search" vs "watchlist" changes.
    """
    details = await asyncio.to_thread(fetch_details, key_id)

    if not details:
        await client.send_message(chat_id, "❌ Could not find details for this title.")
        return

    total_episodes = _total_episodes(key_id, details)

    caption = format_imdb_details(details, total_episodes=total_episodes)

    poster = details.get("Poster")
    poster = poster if poster and poster != "N/A" else None

    if in_watchlist is None:
        # Auto-detect - falls back to False (Add) if we have no user_id to check.
        in_watchlist = await is_in_watchlist(user_id, key_id) if user_id else False

    buttons = build_details_keyboard(key_id, in_watchlist, context=context)

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
        # Fallback to text if the poster URL fails to load as a photo
        await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=buttons
        )


async def send_imdb_details_inline(client, inline_message_id, key_id, user_id=None):
    """Edit an inline-inserted search-result card into the full details
    page (poster + full info caption + Watchlist/Search Another/Done
    buttons), in place, via its inline_message_id. Called from
    plugins/inline.py's inline_result_chosen() for both SEARCH - IMDb and
    SEARCH - TMDb results.
    """
    details = await asyncio.to_thread(fetch_details, key_id)

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

    total_episodes = _total_episodes(key_id, details)

    caption = format_imdb_details(details, total_episodes=total_episodes)

    in_watchlist = await is_in_watchlist(user_id, key_id) if user_id else False

    buttons = build_details_keyboard(key_id, in_watchlist, context="search")

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
