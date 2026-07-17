from pyrogram import Client
from pyrogram.types import CallbackQuery

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

from plugins.movie import (
    recommendations as movie_recommendations,
)

from plugins.series import (
    recommendations as series_recommendations,
)

from plugins.details import (
    get_movie_info,
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

        rating = float(data.replace("rating_", ""))

        set_state(user_id, "rating", rating)

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

    if data.startswith("movie_"):

        movie_id = data.replace("movie_", "")

        if movie_id.isdigit():

            poster, caption = get_movie_info(int(movie_id))

            if caption is None:

                await callback.answer(
                    "Movie not found.",
                    show_alert=True
                )
                return

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

    if data.startswith("page_"):

        from database.user_state import get_results

        page = int(data.replace("page_", ""))

        results = get_results(user_id)

        if not results:

            await callback.answer(
                "Session expired. Please search again.",
                show_alert=True
            )
            return

        await callback.message.edit_reply_markup(
            reply_markup=result_keyboard(results, page)
        )

        await callback.answer()
        return

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


