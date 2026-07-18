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

# ✅ NEW: Watchlist database helpers (Feature 4 & 5)
from database.watchlist_db import add_to_watchlist, get_watchlist

# ✅ NEW: OMDb + YouTube services (Feature 1, 2 & 3)
from services.omdb import get_details
from services.youtube import get_trailer_url

# ✅ NEW: Shared UI helper for rendering result/watchlist cards
from utils.ui import send_result_cards

from plugins.movie import (
    recommendations as movie_recommendations,
)

from plugins.series import (
    recommendations as series_recommendations,
)

from plugins.details import (
    get_movie_info,
    get_series_info,  # ✅ NEW
    send_omdb_details,  # ✅ NEW: Feature 2 & 3 details renderer
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

    if data == "find_movies":

        # Mark this user as "waiting to type a search query"
        set_state(user_id, "awaiting_search", True)

        await callback.message.edit_text(
            "🔍 **Find Movies & Series**\n\n"
            "Type the name of a movie or TV series you want to search for.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Home", callback_data="back_home")]]
            )
        )

        await callback.answer()
        return

    # ---------------- SEARCH RESULT SELECTED (Feature 1 -> Feature 2) ----------------

    if data.startswith("sr_"):

        imdb_id = data.replace("sr_", "", 1)

        await send_omdb_details(client, callback.message.chat.id, imdb_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST: OPEN LIST (Feature 4) ----------------

    if data == "wl_open":

        items = await get_watchlist(user_id)

        if not items:
            await callback.answer("Your watchlist is empty.", show_alert=True)
            return

        # Convert stored DB docs into the shared card format used by send_result_cards
        cards = [
            {
                "Title": doc.get("title"),
                "Year": doc.get("year"),
                "Poster": doc.get("poster"),
                "imdbID": doc.get("imdb_id"),
                "Type": doc.get("media_type", "movie"),
            }
            for doc in items
        ]

        await callback.answer()
        await send_result_cards(client, callback.message.chat.id, cards, "wl_")
        return

    # ---------------- WATCHLIST: ITEM SELECTED (Feature 4 -> Feature 2) ----------------

    if data.startswith("wl_"):

        imdb_id = data.replace("wl_", "", 1)

        await send_omdb_details(client, callback.message.chat.id, imdb_id)

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

        if added:
            await callback.answer("Added to Watchlist ✅", show_alert=True)
        else:
            await callback.answer("Already in your Watchlist.", show_alert=True)

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
        # ✅ Convert to float and add small offset to make "6+" mean "> 6" instead of ">= 6"
        rating = float(rating_value)
        # Add 0.01 to ensure we get strictly greater than, not equal to
        rating = rating + 0.01 if rating > 0 else rating

        set_state(user_id, "rating", rating)

        # ✅ FIX: state was used below without being fetched first (NameError)
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

    # ---------------- MOVIE DETAILS ----------------

# ✅ Handles both movies and series
    if data.startswith("movie_"):
        item_id = data.replace("movie_", "")
        if item_id.isdigit():
            # ✅ Check user state to determine if series or movie
            state = get_state(user_id)
            is_series = state.get("type") == "series"

            if is_series:
                poster, caption = get_series_info(int(item_id))  # ✅ Series
                error_msg = "Series not found."
            else:
                poster, caption = get_movie_info(int(item_id))  # Movie
                error_msg = "Movie not found."

            if caption is None:
                await callback.answer(error_msg, show_alert=True)
                return
            # ... send photo/message

            if poster:

                await client.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=poster,
                    caption=caption
                )

            else:

                await callback.message.reply_text(caption)

            await callback.answer()
            return

    # ---------------- PAGINATION ----------------

    # ✅ REMOVED: Entire pagination handler deleted
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
