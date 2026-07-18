from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.home import home_keyboard
from keyboards.type import type_keyboard
from keyboards.genre import genre_keyboard
from keyboards.language import language_keyboard
from keyboards.rating import rating_keyboard
from keyboards.result import result_keyboard

from database.user_state import (
    set_state,
    get_state,
    clear_state,
)

# Watchlist database helpers (Feature 5)
from database.watchlist_db import add_to_watchlist, remove_from_watchlist

# Feature 4 - shared watchlist text/keyboard builder + the
# delete-then-resend helper, used by the Watchlist Home button
# (callback_data="watchlist_open" below) and by the /watchlist command in
# plugins/watchlist.py. Everything renders inside this Telegram chat - no
# Web App / external page.
from plugins.watchlist import send_watchlist_view

# OMDb + YouTube services (Feature 1, 2 & 3)
from services.omdb import get_details
from services.youtube import get_trailer_url

# Shared UI helper for rendering search-result cards
from utils.ui import send_result_cards

from plugins.movie import (
    recommendations as movie_recommendations,
)

from plugins.series import (
    recommendations as series_recommendations,
)

from plugins.details import (
    send_omdb_details,       # Feature 2 & 3 details renderer (Find Movies / Watchlist)
    send_suggested_details,  # Feature 2 details renderer (Suggest Me)
    build_details_keyboard,  # Shared Trailer/Watchlist/Done keyboard builder
)


@Client.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):

    data = callback.data
    user_id = callback.from_user.id

    # ---------------- HOME ----------------

    if data == "suggest_me":

        clear_state(user_id)

        await callback.message.edit_text(
            "🎬 **Select what you're looking for**",
            reply_markup=type_keyboard()
        )

        await callback.answer()
        return

    if data == "back_home":

        clear_state(user_id)

        await callback.message.edit_text(
            text=(
                "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
                "🎬 Discover Movies & TV Series based on:\n\n"
                "• 🎭 Genre\n"
                "• 🌍 Language\n"
                "• ⭐ IMDb Rating\n\n"
                "Click the button below to start."
            ),
            reply_markup=home_keyboard()
        )

        await callback.answer()
        return

    # ---------------- FIND MOVIES (Feature 1) ----------------
    # "Find Movies & Series" is handled entirely by Telegram Inline Mode
    # (see keyboards/home.py + plugins/inline.py). The button doesn't send
    # callback_data, so there's nothing to handle here.

    # ---------------- SEARCH RESULT SELECTED (Feature 1 -> Feature 2) ----------------
    # Fired when the user taps "View Details" on a card sent either from
    # an inline search result (plugins/inline.py) or from search listings.

    if data.startswith("sr_"):

        imdb_id = data.replace("sr_", "", 1)

        # FIX: Cards selected from an inline search (the "via @BotName"
        # messages Telegram inserts directly, as in plugins/inline.py) are
        # NOT sent by the bot itself, so Pyrogram gives us
        # callback.message == None (only callback.inline_message_id is set
        # for those). The old code unconditionally read
        # callback.message.chat.id, which raised an AttributeError before
        # callback.answer() ran, so tapping "View Details" on an inline
        # result silently did nothing. Fall back to the user's own chat,
        # which is where these inline cards are actually viewed.
        chat_id = callback.message.chat.id if callback.message else callback.from_user.id

        # NEW (Feature 4): Once the full details page is on its way, get
        # rid of the search-result card that was tapped so it doesn't stay
        # behind. A card sent directly by the bot (search flows using
        # utils/ui.py) can simply be deleted. A card that Telegram inserted
        # from an inline query result (plugins/inline.py) only gives us an
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

        # user_id passed so send_omdb_details auto-detects whether this
        # title is already saved and shows the correct button (Feature 3 fix).
        # context="search" (default) -> this is a "Find Movies & Series"
        # details page: Delete from Watchlist toggles in place and a Done
        # button is shown (Feature 4 & 5).
        await send_omdb_details(client, chat_id, imdb_id, user_id=user_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST (Feature 4) ----------------
    # CHANGED: The watchlist now works completely inside this Telegram
    # chat - no Web App / Mini App / external page. Tapping the Watchlist
    # Home button sends "watchlist_open", which prints the user's saved
    # titles as a numbered text list with numbered inline buttons
    # underneath (plugins/watchlist.py + keyboards/watchlist.py).

    if data == "watchlist_open":

        # CHANGED: Use the shared delete-then-resend helper instead of
        # editing the Home menu message in place. This keeps the "last
        # watchlist message" tracked consistently so later refreshes
        # (after add/delete) always remove the right message and never
        # leave duplicate listings stacked in the chat.
        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_watchlist_view(client, callback.message.chat.id, user_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST: ITEM SELECTED (Feature 4 -> Feature 2) ----------------
    # Fired when the user taps one of the numbered buttons under the
    # watchlist listing above ("wl_<imdbID>") - shows that title's full
    # details page, same as a Find Movies search result.

    if data.startswith("wl_"):

        imdb_id = data.replace("wl_", "", 1)

        # in_watchlist=True -> shows Delete from Watchlist instead of Add
        # to Watchlist, since this title is already saved (it came from
        # the user's own watchlist listing).
        # context="watchlist" -> keeps the ORIGINAL behavior for this
        # entry point: tapping Delete removes the item, deletes this
        # message, and refreshes the watchlist listing. A "✅ Done" button
        # is also shown here (Feature 6) so the user can dismiss the
        # details message on its own without deleting the saved item.
        await send_omdb_details(
            client, callback.message.chat.id, imdb_id,
            user_id=user_id, in_watchlist=True, context="watchlist",
        )

        await callback.answer()
        return

    # ---------------- SUGGEST ME: ITEM SELECTED (Feature 2) ----------------
    # Fired when the user taps a numbered button under a "Suggest Me"
    # recommendation list ("movie_<tmdbID>", where the id is a TMDB id).
    # Shows the exact same details page (info + Trailer / Watchlist /
    # Done buttons) as "Find Movies & Series".

    if data.startswith("movie_"):
        item_id = data.replace("movie_", "")
        if item_id.isdigit():
            # Check user state to determine if series or movie
            state = get_state(user_id)
            media_type = "series" if state.get("type") == "series" else "movie"

            await send_suggested_details(
                client, callback.message.chat.id, int(item_id),
                media_type, user_id=user_id,
            )

            await callback.answer()
            return

    # ---------------- TRAILER (Feature 3) ----------------

    if data.startswith("trailer_"):

        imdb_id = data.replace("trailer_", "", 1)

        details = get_details(imdb_id)

        if not details:
            await callback.answer("Trailer not available.", show_alert=True)
            return

        trailer_url = get_trailer_url(details.get("Title"), details.get("Year"))

        if not trailer_url:
            await callback.answer("Trailer not available.", show_alert=True)
            return

        await callback.message.reply_text(
            f"🎬 Trailer for **{details.get('Title')}**",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("▶️ Watch on YouTube", url=trailer_url)]]
            )
        )

        await callback.answer()
        return

    # ---------------- ADD TO WATCHLIST (Feature 3 -> Feature 5) ----------------
    # Fired from a "Find Movies & Series" or "Suggest Me" details page
    # (the only places an "Add to Watchlist" button can appear - the
    # Watchlist listing's own details page always starts already saved).
    #
    # After adding, the button on this same details message is swapped to
    # "Delete from Watchlist" IN PLACE, keeping the Trailer and Done
    # buttons intact (Feature 2 & 4 fix).

    if data.startswith("addwl_"):

        imdb_id = data.replace("addwl_", "", 1)

        details = get_details(imdb_id)

        if not details:
            await callback.answer("Could not add this title. Please try again.", show_alert=True)
            return

        poster = details.get("Poster")
        poster = poster if poster and poster != "N/A" else None

        added = await add_to_watchlist(
            user_id=user_id,
            imdb_id=imdb_id,
            title=details.get("Title"),
            poster=poster,
            year=details.get("Year"),
            media_type=details.get("Type", "movie"),
        )

        if callback.message:
            # This button only ever appears on a "search"-context (Find
            # Movies & Series / Suggest Me) details page, so rebuild with
            # the same context: Trailer + Delete from Watchlist (toggles
            # in place from here on) + Done.
            new_markup = build_details_keyboard(imdb_id, in_watchlist=True, context="search")
            try:
                await callback.message.edit_reply_markup(reply_markup=new_markup)
            except Exception:
                pass
        elif callback.inline_message_id:
            # NEW (Feature 6): details page opened directly from an inline
            # search result (plugins/inline.py's inline_result_chosen()) -
            # there's no chat message object here, only an
            # inline_message_id, so the keyboard has to be rebuilt with a
            # real Trailer URL button (context="inline") and pushed via
            # edit_inline_reply_markup instead of edit_reply_markup.
            trailer_url = get_trailer_url(details.get("Title"), details.get("Year"))
            new_markup = build_details_keyboard(
                imdb_id, in_watchlist=True, context="inline", trailer_url=trailer_url
            )
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

    # ---------------- REMOVE FROM WATCHLIST, IN PLACE (Feature 4) ----------------
    # Fired when "Delete from Watchlist" is tapped on a "Find Movies &
    # Series" or "Suggest Me" details page. Unlike the Watchlist listing's
    # own Delete button below, this does NOT delete the message or open
    # the watchlist - it removes the title from the database, shows a
    # popup confirmation, and swaps the button back to "Add to Watchlist"
    # on the same message.

    if data.startswith("rmwl_"):

        imdb_id = data.replace("rmwl_", "", 1)

        await remove_from_watchlist(user_id, imdb_id)

        if callback.message:
            new_markup = build_details_keyboard(imdb_id, in_watchlist=False, context="search")
            try:
                await callback.message.edit_reply_markup(reply_markup=new_markup)
            except Exception:
                pass
        elif callback.inline_message_id:
            # NEW (Feature 6): same inline-details case as "addwl_" above.
            details = get_details(imdb_id)
            trailer_url = (
                get_trailer_url(details.get("Title"), details.get("Year"))
                if details else None
            )
            new_markup = build_details_keyboard(
                imdb_id, in_watchlist=False, context="inline", trailer_url=trailer_url
            )
            try:
                await client.edit_inline_reply_markup(
                    callback.inline_message_id, reply_markup=new_markup
                )
            except Exception:
                pass

        await callback.answer("Removed from Watchlist 🗑", show_alert=True)
        return

    # ---------------- DONE (Feature 5 & 6) ----------------
    # Fired when "✅ Done" is tapped on any details page - "Find Movies &
    # Series", "Suggest Me", the Watchlist's own details page, or (NEW,
    # Feature 6) the full-details page shown automatically after picking a
    # title from an inline search. This only dismisses/clears that details
    # message - it never touches the saved watchlist entry itself.

    if data == "done":

        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        elif callback.inline_message_id:
            # NEW (Feature 6): a message inserted via inline mode can't be
            # deleted through the Bot API - the closest available action
            # is clearing its buttons and marking it as dismissed, same
            # fallback already used for "sr_" above.
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

    # ---------------- DELETE FROM WATCHLIST (Feature 4) ----------------
    # Fired when the user taps "Delete from Watchlist" on a details page
    # opened from the Watchlist itself (the "wl_" handler above, the only
    # entry point that uses context="watchlist"). Behavior is unchanged:
    # the item is removed, this details message is deleted, and the
    # watchlist listing is refreshed.

    if data.startswith("delwl_"):

        imdb_id = data.replace("delwl_", "", 1)

        await remove_from_watchlist(user_id, imdb_id)

        chat_id = callback.message.chat.id

        # CHANGED: Remove the details message entirely, then refresh the
        # watchlist listing using the shared delete-then-resend helper so
        # the deleted item disappears and no duplicate listing message is
        # left behind (Feature 1 & 4 fix).
        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_watchlist_view(client, chat_id, user_id)

        await callback.answer("Removed from Watchlist 🗑")
        return

    # ---------------- MOVIES ----------------

    if data == "movies":

        set_state(user_id, "type", "movie")

        await callback.message.edit_text(
            "🎬 **Choose a Movie Genre**",
            reply_markup=genre_keyboard("movie")
        )

        await callback.answer()
        return

    # ---------------- SERIES ----------------

    if data == "series":

        set_state(user_id, "type", "series")

        await callback.message.edit_text(
            "📺 **Choose a Series Genre**",
            reply_markup=genre_keyboard("series")
        )

        await callback.answer()
        return

    # ---------------- GENRE ----------------

    if data.startswith("movie_"):

        value = data.replace("movie_", "")

        # Ignore movie detail callbacks
        if not value.isdigit():

            set_state(user_id, "genre", value)

            await callback.message.edit_text(
                "🌍 **Choose Language**",
                reply_markup=language_keyboard()
            )

            await callback.answer()
            return

    if data.startswith("series_"):

        value = data.replace("series_", "")

        set_state(user_id, "genre", value)

        await callback.message.edit_text(
            "🌍 **Choose Language**",
            reply_markup=language_keyboard()
        )

        await callback.answer()
        return

    # ---------------- LANGUAGE ----------------

    if data.startswith("language_"):

        language = data.replace("language_", "")

        set_state(user_id, "language", language)

        await callback.message.edit_text(
            "⭐ **Choose Minimum IMDb Rating**",
            reply_markup=rating_keyboard()
        )

        await callback.answer()
        return
    # ---------------- RATING ----------------

    if data.startswith("rating_"):
        rating_value = data.replace("rating_", "")
        # Convert to float and add small offset to make "6+" mean "> 6" instead of ">= 6"
        rating = float(rating_value)
        # Add 0.01 to ensure we get strictly greater than, not equal to
        rating = rating + 0.01 if rating > 0 else rating

        set_state(user_id, "rating", rating)

        # FIX: state was used below without being fetched first (NameError)
        state = get_state(user_id)

        if state.get("type") == "movie":
            text, results = movie_recommendations(user_id)
        else:
            text, results = series_recommendations(user_id)

        # Save results for pagination
        from database.user_state import save_results

        save_results(user_id, results)

        await callback.message.edit_text(
            text=text,
            reply_markup=result_keyboard(results, page=1)
        )

        await callback.answer()
        return

    # ---------------- PAGINATION ----------------

    # REMOVED: Entire pagination handler deleted
    # (No need for page handling since we only show 10 items)

    # ---------------- BACK ----------------

    if data == "back_language":

        await callback.message.edit_text(
            "🌍 **Choose Language**",
            reply_markup=language_keyboard()
        )

        await callback.answer()
        return

    # ---------------- UNKNOWN ----------------

    await callback.answer()
