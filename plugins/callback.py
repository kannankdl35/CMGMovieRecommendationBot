import asyncio

from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.home import home_keyboard

# 🔥 Trending Now keyboards (Today/This Week/Home selection page + the
# numbered listing keyboard), and the TMDb trending fetcher.
from keyboards.trending import trending_menu_keyboard, trending_list_keyboard
from services.tmdb import get_trending_tmdb

# Per-user in-memory storage of the last trending listing fetched, so the
# numbered buttons under it can be mapped back to a title (see
# database/user_state.py).
from database.user_state import save_trending_results, get_trending_results

# Watchlist database helpers
from database.watchlist_db import add_to_watchlist, remove_from_watchlist

# Shared watchlist text/keyboard builder + the delete-then-resend helper,
# used by the Watchlist Home button (callback_data="watchlist_open" below)
# and by the /watchlist command in plugins/watchlist.py. Everything renders
# inside this Telegram chat - no Web App / external page.
from plugins.watchlist import send_watchlist_view

from plugins.details import (
    send_imdb_details,        # details renderer (search results / watchlist)
    send_trending_details,     # details renderer for 🔥 Trending Now (adds OTT status)
    fetch_details,             # resolves an IMDb id or a TMDb key to details
    build_details_keyboard,    # shared Watchlist/Search Another/Done keyboard builder
)


@Client.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):

    data = callback.data
    user_id = callback.from_user.id

    # ---------------- HOME ----------------

    if data == "back_home":

        await callback.message.edit_text(
            text=(
                "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
                "🎬 Find any Movie or TV Series and see its full details -\n"
                "poster, rating, cast, and plot.\n\n"
                "• 🔍 **SEARCH - IMDb** - search powered by IMDb\n"
                "• 🔍 **SEARCH - TMDb** - search powered by TMDb\n"
                "• 🔥 **TRENDING NOW** - what's trending today/this week on TMDb\n"
                "• 📋 **WATCHLIST** - your saved titles\n\n"
                "Click a button below to get started."
            ),
            reply_markup=home_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: MENU ----------------
    # Fired from the main menu's "🔥 Trending Now" button
    # (callback_data="trending_open", see keyboards/home.py). Shows the
    # Today / This Week / Home selection page (keyboards/trending.py),
    # edited in place over the main menu message.

    if data == "trending_open":

        await callback.message.edit_text(
            text=(
                "🔥 **Trending Now**\n\n"
                "See what's trending on TMDb right now.\n\n"
                "• 📅 **Today** - trending today\n"
                "• 📈 **This Week** - trending this week\n\n"
                "Pick one below 👇"
            ),
            reply_markup=trending_menu_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: TODAY / THIS WEEK ----------------
    # Fetches TMDb's daily/weekly trending titles, stores them for this
    # user (so the numbered buttons below can be mapped back to a title -
    # database/user_state.py), and shows them as a numbered list with
    # numbered buttons underneath (keyboards/trending.py's
    # trending_list_keyboard()), 5 per row.

    if data in ("trending_day", "trending_week"):

        period = "day" if data == "trending_day" else "week"
        period_label = "Today" if period == "day" else "This Week"

        results = await asyncio.to_thread(get_trending_tmdb, period)

        # API failure (network error, bad key, non-2xx) - get_trending_tmdb()
        # returns None in that case, distinct from a successful-but-empty list.
        if results is None:
            await callback.answer(
                "⚠️ Couldn't fetch trending titles right now. Please try again.",
                show_alert=True,
            )
            return

        save_trending_results(user_id, results)

        if not results:
            await callback.message.edit_text(
                text=f"😕 No trending titles found for **{period_label}** right now.",
                reply_markup=trending_menu_keyboard()
            )
            await callback.answer()
            return

        lines = [f"🔥 **Trending - {period_label}**\n"]

        for index, item in enumerate(results, start=1):
            icon = "📺" if item.get("Type") == "series" else "🎬"
            lines.append(f"{index}. {icon} {item.get('Title')} ({item.get('Year')})")

        lines.append("\nTap a number below to see full details 👇")

        await callback.message.edit_text(
            text="\n".join(lines),
            reply_markup=trending_list_keyboard(len(results))
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: BACK ----------------
    # Fired from "⬅ Back" under a trending listing - returns to the
    # Today / This Week / Home selection page (NOT the main menu).

    if data == "trend_back":

        await callback.message.edit_text(
            text=(
                "🔥 **Trending Now**\n\n"
                "See what's trending on TMDb right now.\n\n"
                "• 📅 **Today** - trending today\n"
                "• 📈 **This Week** - trending this week\n\n"
                "Pick one below 👇"
            ),
            reply_markup=trending_menu_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: ITEM SELECTED ----------------
    # Fired when the user taps one of the numbered buttons under a
    # trending listing ("trend_sel_<n>"). Looks up item `n` in the
    # trending results this user last fetched, and sends its full details
    # page (poster + info + OTT Release Status) as a NEW message - the
    # trending listing itself is left in place so "⬅ Back" still works.

    if data.startswith("trend_sel_"):

        try:
            index = int(data.replace("trend_sel_", "", 1))
        except ValueError:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        results = get_trending_results(user_id)

        if not results or index < 1 or index > len(results):
            await callback.answer(
                "This trending list has expired. Please reopen 🔥 Trending Now.",
                show_alert=True,
            )
            return

        key_id = results[index - 1].get("imdbID")

        await send_trending_details(
            client, callback.message.chat.id, key_id, user_id=user_id
        )

        await callback.answer()
        return

    # ---------------- SEARCH (SEARCH - IMDb / SEARCH - TMDb) ----------------
    # Both search buttons are handled entirely by Telegram Inline Mode (see
    # keyboards/home.py + plugins/inline.py). The buttons don't send
    # callback_data, so there's nothing to handle here.

    # ---------------- SEARCH RESULT SELECTED ----------------
    # Fired when the user taps "View Details" on a card sent from an inline
    # search result (plugins/inline.py). `imdb_id` here is either a real
    # IMDb id (SEARCH - IMDb) or a TMDb key like "tmdb_movie_603"
    # (SEARCH - TMDb) - fetch_details()/send_imdb_details() in
    # plugins/details.py both already know how to tell those apart.

    if data.startswith("sr_"):

        imdb_id = data.replace("sr_", "", 1)

        # Cards selected from an inline search (the "via @BotName" messages
        # Telegram inserts directly) are NOT sent by the bot itself, so
        # Pyrogram gives us callback.message == None (only
        # callback.inline_message_id is set for those). Fall back to the
        # user's own chat, which is where these inline cards are actually
        # viewed.
        chat_id = callback.message.chat.id if callback.message else callback.from_user.id

        # Once the full details page is on its way, get rid of the
        # search-result card that was tapped so it doesn't stay behind. A
        # card sent directly by the bot can simply be deleted. A card that
        # Telegram inserted from an inline query result only gives us an
        # inline_message_id - the Bot API has no way to delete that kind of
        # message, so the closest available cleanup is editing it to show
        # it's already been opened.
        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_text(
                    inline_message_id=callback.inline_message_id,
                    text="✅ Details opened below.",
                )
            except Exception:
                try:
                    await client.edit_inline_caption(
                        inline_message_id=callback.inline_message_id,
                        caption="✅ Details opened below.",
                    )
                except Exception:
                    pass

        # user_id passed so send_imdb_details auto-detects whether this
        # title is already saved and shows the correct button.
        # context="search" (default) -> Delete from Watchlist toggles in
        # place and a Done button is shown.
        await send_imdb_details(client, chat_id, imdb_id, user_id=user_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST ----------------
    # The watchlist works completely inside this Telegram chat - no Web
    # App / Mini App / external page. Tapping the Watchlist Home button
    # sends "watchlist_open", which prints the user's saved titles as a
    # numbered text list with numbered inline buttons underneath
    # (plugins/watchlist.py + keyboards/watchlist.py).

    if data == "watchlist_open":

        # Use the shared delete-then-resend helper instead of editing the
        # Home menu message in place. This keeps the "last watchlist
        # message" tracked consistently so later refreshes (after
        # add/delete) always remove the right message and never leave
        # duplicate listings stacked in the chat.
        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_watchlist_view(client, callback.message.chat.id, user_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST: ITEM SELECTED ----------------
    # Fired when the user taps one of the numbered buttons under the
    # watchlist listing above ("wl_<key_id>") - shows that title's full
    # details page, same as a search result.
    #
    # ✅ key_id is stored exactly as it was found (a real IMDb id for a
    # SEARCH - IMDb title, or a "tmdb_..." key for a SEARCH - TMDb title -
    # see the "addwl_" handler below), so this always re-fetches from the
    # SAME source the title was originally added from.

    if data.startswith("wl_"):

        imdb_id = data.replace("wl_", "", 1)

        # in_watchlist=True -> shows Delete from Watchlist instead of Add
        # to Watchlist, since this title is already saved (it came from
        # the user's own watchlist listing).
        # context="watchlist" -> keeps the ORIGINAL behavior for this entry
        # point: tapping Delete removes the item, deletes this message, and
        # refreshes the watchlist listing. A "✅ Done" button is also shown
        # here so the user can dismiss the details message on its own
        # without deleting the saved item.
        await send_imdb_details(
            client, callback.message.chat.id, imdb_id,
            user_id=user_id, in_watchlist=True, context="watchlist",
        )

        await callback.answer()
        return

    # ---------------- ADD TO WATCHLIST ----------------
    # Fired from a details page opened from a search result (the only
    # place an "Add to Watchlist" button can appear - the Watchlist
    # listing's own details page always starts already saved).
    #
    # After adding, the button on this same details message is swapped to
    # "Delete from Watchlist" IN PLACE.

    if data.startswith("addwl_"):

        imdb_id = data.replace("addwl_", "", 1)

        details = await asyncio.to_thread(fetch_details, imdb_id)

        if not details:
            await callback.answer("Could not add this title. Please try again.", show_alert=True)
            return

        poster = details.get("Poster")
        poster = poster if poster and poster != "N/A" else None

        # ✅ Always store the id exactly as tapped (imdb_id) - NOT any
        # "resolved" id from `details` - so a title found via SEARCH - TMDb
        # stays keyed by its "tmdb_..." id, and a title found via
        # SEARCH - IMDb stays keyed by its real "tt..." id. This is what
        # makes the "wl_" handler above always re-open from the same
        # source the title was added from.
        added = await add_to_watchlist(
            user_id=user_id,
            imdb_id=imdb_id,
            title=details.get("Title"),
            poster=poster,
            year=details.get("Year"),
            media_type=details.get("Type", "movie"),
        )

        new_markup = build_details_keyboard(imdb_id, in_watchlist=True, context="search")

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=new_markup)
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_reply_markup(
                    callback.inline_message_id, reply_markup=new_markup
                )
            except Exception:
                pass

        if added:
            await callback.answer("Added to Watchlist ✅")
        else:
            await callback.answer("Already in your Watchlist.")

        return

    # ---------------- REMOVE FROM WATCHLIST, IN PLACE ----------------
    # Fired when "Delete from Watchlist" is tapped on a search-result
    # details page. Unlike the Watchlist listing's own Delete button below,
    # this does NOT delete the message or open the watchlist - it removes
    # the title from the database, shows a popup confirmation, and swaps
    # the button back to "Add to Watchlist" on the same message.

    if data.startswith("rmwl_"):

        imdb_id = data.replace("rmwl_", "", 1)

        await remove_from_watchlist(user_id, imdb_id)

        new_markup = build_details_keyboard(imdb_id, in_watchlist=False, context="search")

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=new_markup)
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_reply_markup(
                    callback.inline_message_id, reply_markup=new_markup
                )
            except Exception:
                pass

        await callback.answer("Removed from Watchlist 🗑", show_alert=True)
        return

    # ---------------- DONE ----------------
    # Fired when "✅ Done" is tapped on any details page. This only
    # dismisses/clears that details message - it never touches the saved
    # watchlist entry itself.

    if data == "done":

        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        elif callback.inline_message_id:
            # A message inserted via inline mode can't be deleted through
            # the Bot API - the closest available action is clearing its
            # buttons and marking it as dismissed, same fallback already
            # used for "sr_" above.
            try:
                await client.edit_inline_caption(
                    callback.inline_message_id, "✅ Done.", reply_markup=None
                )
            except Exception:
                try:
                    await client.edit_inline_text(
                        callback.inline_message_id, "✅ Done.", reply_markup=None
                    )
                except Exception:
                    pass

        await callback.answer()
        return

    # ---------------- DELETE FROM WATCHLIST ----------------
    # Fired when the user taps "Delete from Watchlist" on a details page
    # opened from the Watchlist itself (the "wl_" handler above, the only
    # entry point that uses context="watchlist"). The item is removed, this
    # details message is deleted, and the watchlist listing is refreshed.

    if data.startswith("delwl_"):

        imdb_id = data.replace("delwl_", "", 1)

        await remove_from_watchlist(user_id, imdb_id)

        chat_id = callback.message.chat.id

        # Remove the details message entirely, then refresh the watchlist
        # listing using the shared delete-then-resend helper so the
        # deleted item disappears and no duplicate listing message is left
        # behind.
        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_watchlist_view(client, chat_id, user_id)

        await callback.answer("Removed from Watchlist 🗑")
        return

    # ---------------- UNKNOWN ----------------

    await callback.answer()
