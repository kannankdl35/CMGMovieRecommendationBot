# Location: plugins/details.py  (REPLACE ENTIRE FILE)

import asyncio

# IMDb + TMDb detail lookup & formatter, used by both search flows
# (SEARCH - IMDb / SEARCH - TMDb) and by the Watchlist / This Month Watched.
from services.imdb import get_details, get_series_episode_count
from services.tmdb import get_details_tmdb
from utils.formatter import format_imdb_details
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Used to auto-detect whether a title is already saved, so the correct
# watchlist button (Add vs Delete) is shown regardless of where the details
# page was opened from.
from database.watchlist_db import is_in_watchlist

# ✅ NEW - "This Month Watched" feature: same auto-detect pattern as
# is_in_watchlist above, so the correct button ("➕ Add to This Month
# Watched" vs "➖ Delete from This Month Watched") is shown regardless of
# where the details page was opened from.
from database.month_watched_db import is_in_month_watched

# ✅ NEW - ⚙️ Settings feature: per-user IMDb/TMDb field visibility,
# looked up here (keyed by details["Source"]) and applied to every details
# page this module builds - see database/settings_db.py and the ⚙️
# Settings menu in plugins/callback.py / keyboards/settings.py.
from database.settings_db import get_settings as get_display_settings


def _source_mode(key_id):
    """"tmdb" for a TMDb-sourced key ("tmdb_movie_603" / "tmdb_tv_1396"),
    "imdb" for a real IMDb id ("tt1234567") - see services/tmdb.py."""
    return "tmdb" if key_id and key_id.startswith("tmdb_") else "imdb"


def fetch_details(key_id):
    """Resolve full details for either an IMDb id ("tt1234567", from the
    SEARCH - IMDb flow) or a TMDb-sourced key ("tmdb_movie_603" /
    "tmdb_tv_1396", from the SEARCH - TMDb flow - see services/tmdb.py).

    This is the single place that decides which backend to call - every
    other part of the bot (watchlist, this month watched, add/remove
    buttons, plugins/callback.py, plugins/inline.py) just passes whichever
    key_id it was originally given straight through to this function. This
    makes a blocking HTTP request - call it via asyncio.to_thread() from
    async code (see send_imdb_details() below) rather than awaiting it
    directly.
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


async def _resolve_display(user_id, details):
    """✅ NEW - ⚙️ Settings feature: look up this user's saved field
    visibility settings for whichever source ("imdb"/"tmdb") `details`
    came from, and apply them to the Poster - the poster is sent as the
    photo/attachment itself rather than a caption line, so (unlike every
    other toggleable field) it can't be filtered inside
    utils/formatter.py's format_imdb_details() and is resolved here
    instead.

    Returns (poster_url_or_None, enabled_fields_dict). `enabled_fields` is
    passed straight through to format_imdb_details() by every caller
    below. Falls back to "everything enabled" when there's no user_id to
    look up (get_display_settings() already handles user_id=None) - same
    fallback pattern used for in_watchlist/in_month_watched elsewhere in
    this file.
    """
    source = details.get("Source", "imdb")
    enabled_fields = await get_display_settings(user_id, source)

    poster = details.get("Poster")
    if not poster or poster == "N/A" or not enabled_fields.get("poster", True):
        poster = None

    return poster, enabled_fields


def build_details_keyboard(
    key_id, in_watchlist, in_month_watched=False, context="search", show_home=False
):
    """Build the Watchlist (Add or Delete) / This Month Watched (Add or
    Delete) / Done (+ optional Search Another / Home) inline keyboard shown
    under a details page.

    "🔎 Search Another Movie/Series" is ONLY included when show_home=True,
    i.e. only for details pages opened from the SEARCH - IMDb / SEARCH -
    TMDb inline search results - see the show_home docstring below. It is
    never shown for 🔥 Trending Now, 🎬 Upcoming Movies, 🎲 Suggest Random
    Movie, the Watchlist listing, or the This Month Watched listing.

    `show_home` controls an extra "🏠 Home" button placed in the SAME ROW as
    "✅ Done" (per the requested layout). This is ONLY turned on for details
    pages opened from the SEARCH - IMDb / SEARCH - TMDb inline search
    results (see send_imdb_details_inline() below, and the "sr_" fallback
    branch in plugins/callback.py) - NOT for 🔥 Trending Now, 🎬 Upcoming
    Movies, 🎲 Suggest Random Movie, the Watchlist listing, or the This
    Month Watched listing, which never pass show_home=True.

    Tapping "🏠 Home" fires callback_data "home_from_search" (handled in
    plugins/callback.py), which closes this details message and sends a
    fresh Home menu message - deliberately a different callback_data than
    the plain-text listing pages' "back_home" button (keyboards/trending.py,
    keyboards/upcoming.py, keyboards/random_movies.py, keyboards/watchlist.py,
    keyboards/month_watched.py), since THIS details message is very often a
    photo (poster + caption) rather than plain text, so it can't just be
    edited in place into the Home menu text the way those listing pages are.

    Because tapping "❤️ Add to Watchlist" / "🗑 Delete from Watchlist" /
    "➕ Add to This Month Watched" / "➖ Delete from This Month Watched"
    rebuilds this same keyboard IN PLACE (see the addwl_/rmwl_/addmw_/rmmw_
    branches in plugins/callback.py), whether the Home button should still
    be there after one of those taps has to survive the round trip. Since
    Telegram only reports callback_data (not which context the message was
    built with), this is encoded directly in those four buttons'
    callback_data with a trailing "h" marker on the action name whenever
    show_home is True (e.g. "addwlh_<key_id>" instead of "addwl_<key_id>") -
    plugins/callback.py checks for both the plain and "h"-suffixed forms of
    each action and reconstructs the keyboard with the same show_home value
    either way.

    `context` controls how BOTH toggle buttons behave once tapped:

    - "search" (default): used for SEARCH - IMDb / SEARCH - TMDb results,
      🔥 Trending Now, 🎬 Upcoming Movies, 🎲 Suggest a Movie (including the
      details page shown right after picking an inline result - see
      plugins/inline.py's inline_result_chosen()).
        * Watchlist:
            Add    -> callback_data "addwl_<key_id>"
            Delete -> callback_data "rmwl_<key_id>": removes the item from
                      the database, shows a popup confirmation, and swaps
                      the button back to "Add to Watchlist" IN PLACE - the
                      message itself is never deleted.
        * This Month Watched:
            Add    -> callback_data "addmw_<key_id>"
            Delete -> callback_data "rmmw_<key_id>": same in-place swap as
                      rmwl_ above.
    - "watchlist": used for details opened from the user's own
      /watchlist listing.
        * Watchlist Delete -> callback_data "delwl_<key_id>": removes the
          item, deletes this details message, and refreshes the watchlist
          listing.
        * This Month Watched button still behaves like "search" (in place)
          since it's unrelated to the Watchlist listing this page was
          opened from.
    - "month_watched": used for details opened from the user's own
      "🗓️ This Month Watched" listing.
        * This Month Watched Delete -> callback_data "delmw_<key_id>":
          removes the item, deletes this details message, and refreshes
          the This Month Watched listing.
        * ❤️ Add to Watchlist / 🗑 Delete from Watchlist button is NOT
          shown at all on this page - a title opened from This Month
          Watched has no Watchlist action here (it also has nothing to do
          with Watchlist membership, since adding to This Month Watched
          already removes a title from the Watchlist - see the "addmw_" /
          "addmwh_" branch in plugins/callback.py).

    "🔎 Search Another Movie/Series" (only shown when show_home=True - see
    above) pre-fills "imdb "/"tmdb " into the chat's inline query box (same
    mechanic as the Home menu's two search buttons, see keyboards/home.py)
    - always for the SAME source this title came from, based on whether
    key_id has a "tmdb_" prefix, so tapping it continues searching on the
    same site as the last result.

    The "✅ Done" button (callback_data "done") is shown for every context.
    Tapping it only dismisses/clears that details message; it never
    touches the saved watchlist or this-month-watched entries themselves.
    When show_home is True, "🏠 Home" (callback_data "home_from_search")
    sits in the SAME ROW, right next to "✅ Done".

    All of these callback_data values are handled in plugins/callback.py.
    """
    # "h" marker carried on the toggle buttons' callback_data so a later
    # add/remove tap (handled in plugins/callback.py) knows to rebuild this
    # keyboard with the same show_home value - see the docstring above.
    home_marker = "h" if show_home else ""

    # ❤️ Add to Watchlist / 🗑 Delete from Watchlist is hidden entirely for
    # details pages opened from the "🗓️ This Month Watched" listing (see
    # the "month_watched" docstring section above) - `watchlist_button`
    # stays None and the row is simply skipped below.
    watchlist_button = None

    if context != "month_watched":
        if in_watchlist:
            if context == "watchlist":
                watchlist_button = InlineKeyboardButton(
                    "🗑 Delete from Watchlist", callback_data=f"delwl_{key_id}"
                )
            else:
                watchlist_button = InlineKeyboardButton(
                    "🗑 Delete from Watchlist", callback_data=f"rmwl{home_marker}_{key_id}"
                )
        else:
            watchlist_button = InlineKeyboardButton(
                "❤️ Add to Watchlist", callback_data=f"addwl{home_marker}_{key_id}"
            )

    if in_month_watched:
        if context == "month_watched":
            month_watched_button = InlineKeyboardButton(
                "➖ Delete from This Month Watched", callback_data=f"delmw_{key_id}"
            )
        else:
            month_watched_button = InlineKeyboardButton(
                "➖ Delete from This Month Watched", callback_data=f"rmmw{home_marker}_{key_id}"
            )
    else:
        month_watched_button = InlineKeyboardButton(
            "➕ Add to This Month Watched", callback_data=f"addmw{home_marker}_{key_id}"
        )

    mode = _source_mode(key_id)

    last_row = [InlineKeyboardButton("✅ Done", callback_data="done")]
    if show_home:
        last_row.append(
            InlineKeyboardButton("🏠 Home", callback_data="home_from_search")
        )

    rows = []
    if watchlist_button is not None:
        rows.append([watchlist_button])
    rows.append([month_watched_button])

    # "🔎 Search Another Movie/Series" is only relevant for details pages
    # opened from the SEARCH - IMDb / SEARCH - TMDb inline search results,
    # which are the only callers that pass show_home=True (see the
    # docstring above and plugins/callback.py's "sr_" fallback branch /
    # plugins/inline.py's inline_result_chosen()). Every other feature
    # (🔥 Trending Now, 🎬 Upcoming Movies, 🎲 Suggest Random Movie, the
    # Watchlist listing, the This Month Watched listing) never passes
    # show_home=True, so they never get this button.
    if show_home:
        rows.append(
            [
                InlineKeyboardButton(
                    "🔎 Search Another Movie/Series",
                    switch_inline_query_current_chat=f"{mode} ",
                )
            ]
        )

    rows.append(last_row)

    return InlineKeyboardMarkup(rows)


async def send_imdb_details(
    client, chat_id, key_id, user_id=None,
    in_watchlist=None, in_month_watched=None, context="search", show_home=False,
):
    """Fetch full details for key_id and send a rich details message with
    Poster, full info caption, and Watchlist / This Month Watched /
    Search Another / Done (+ optional Home) buttons.

    `in_watchlist` / `in_month_watched` each control which state their
    button is shown in:
    - None (default): auto-detect by checking the database for `user_id`
      - this makes the button correct no matter where the details page was
        opened from, instead of trusting the caller to know.
    - True/False: explicit override, used by callers that already know the
      answer (e.g. the Watchlist / This Month Watched listings themselves).

    `context` is passed straight through to build_details_keyboard() - see
    that function for what "search" vs "watchlist" vs "month_watched"
    changes.

    `show_home` is also passed straight through to build_details_keyboard()
    - only the "sr_" fallback branch in plugins/callback.py (SEARCH - IMDb
    / SEARCH - TMDb "ℹ️ View Details" tap) passes show_home=True; every
    other caller leaves it False, per the "only in the IMDb/TMDb search
    result" requirement.
    """
    details = await asyncio.to_thread(fetch_details, key_id)

    if not details:
        await client.send_message(chat_id, "❌ Could not find details for this title.")
        return

    total_episodes = _total_episodes(key_id, details)

    poster, enabled_fields = await _resolve_display(user_id, details)

    caption = format_imdb_details(
        details, total_episodes=total_episodes, enabled_fields=enabled_fields
    )

    if in_watchlist is None:
        # Auto-detect - falls back to False (Add) if we have no user_id to check.
        in_watchlist = await is_in_watchlist(user_id, key_id) if user_id else False

    if in_month_watched is None:
        in_month_watched = await is_in_month_watched(user_id, key_id) if user_id else False

    buttons = build_details_keyboard(
        key_id, in_watchlist, in_month_watched, context=context, show_home=show_home
    )

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


async def send_trending_details(client, chat_id, key_id, user_id=None):
    """🔥 Trending Now details view - same details page as
    send_imdb_details().

    Also used for 🎬 Upcoming Movies and 🎲 Suggest a Movie details pages
    (see plugins/callback.py).

    Trending results are always TMDb-sourced (services.tmdb.get_trending_tmdb()),
    so this always sends a NEW message (kept separate from
    send_imdb_details() rather than adding an `show_ott` flag there) and
    always uses context="search" for the Watchlist / This Month Watched
    buttons: Add/Delete toggles in place on this message, and "✅ Done"
    only deletes this message - the trending listing above it, and the
    watchlist / this month watched list, are both left untouched, per the
    Trending Now spec. Deliberately never passes show_home=True - the
    "🏠 Home" button is reserved for SEARCH - IMDb / SEARCH - TMDb results
    only (see build_details_keyboard()'s docstring), so 🔥 Trending Now /
    🎬 Upcoming Movies / 🎲 Suggest Random Movie details pages keep their
    existing "⬅ Back" / language-menu navigation instead.
    """
    details = await asyncio.to_thread(fetch_details, key_id)

    if not details:
        await client.send_message(
            chat_id, "❌ Could not fetch details for this title. Please try again."
        )
        return

    total_episodes = _total_episodes(key_id, details)

    poster, enabled_fields = await _resolve_display(user_id, details)

    caption = format_imdb_details(
        details, total_episodes=total_episodes, enabled_fields=enabled_fields
    )

    in_watchlist = await is_in_watchlist(user_id, key_id) if user_id else False
    in_month_watched = await is_in_month_watched(user_id, key_id) if user_id else False

    buttons = build_details_keyboard(key_id, in_watchlist, in_month_watched, context="search")

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
    page (poster + full info caption + Watchlist/This Month Watched/Search
    Another/Done/Home buttons), in place, via its inline_message_id. Called
    from plugins/inline.py's inline_result_chosen() for both SEARCH - IMDb
    and SEARCH - TMDb results.

    Always passes show_home=True to build_details_keyboard() - this is one
    of the two entry points for the actual SEARCH - IMDb / SEARCH - TMDb
    flow (the other being the "sr_" fallback branch in
    plugins/callback.py), so the "🏠 Home" button belongs here.
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

    poster, enabled_fields = await _resolve_display(user_id, details)

    caption = format_imdb_details(
        details, total_episodes=total_episodes, enabled_fields=enabled_fields
    )

    in_watchlist = await is_in_watchlist(user_id, key_id) if user_id else False
    in_month_watched = await is_in_month_watched(user_id, key_id) if user_id else False

    buttons = build_details_keyboard(
        key_id, in_watchlist, in_month_watched, context="search", show_home=True
    )

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
