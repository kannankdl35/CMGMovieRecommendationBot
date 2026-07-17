from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.genre import genre_keyboard
from keyboards.language import language_keyboard
from keyboards.rating import rating_keyboard
from keyboards.result import result_keyboard

from database.user_state import set_state, get_state

from services.discover import get_movie_recommendations
from utils.formatter import format_movies


@Client.on_callback_query()
async def movie_callback(client: Client, callback: CallbackQuery):

    data = callback.data
    user_id = callback.from_user.id

    # Movie Button
    if data == "movies":

        set_state(user_id, "type", "movie")

        await callback.message.edit_text(
            "🎬 **Select Movie Genre**",
            reply_markup=genre_keyboard("movie")
        )

    # Genre Selected
    elif data.startswith("movie_"):

        genre = data.replace("movie_", "")

        set_state(user_id, "genre", genre)

        await callback.message.edit_text(
            "🌍 **Select Language**",
            reply_markup=language_keyboard()
        )

    # Language Selected
    elif data.startswith("language_"):

        language = data.replace("language_", "")

        set_state(user_id, "language", language)

        await callback.message.edit_text(
            "⭐ **Select Minimum IMDb Rating**",
            reply_markup=rating_keyboard()
        )

    # Rating Selected
    elif data.startswith("rating_"):

        rating = float(data.replace("rating_", ""))

        set_state(user_id, "rating", rating)

        state = get_state(user_id)

        results = get_movie_recommendations(
            genre=state.get("genre"),
            language=state.get("language"),
            rating=state.get("rating"),
        )

        text = format_movies(results)

        await callback.message.edit_text(
            text=text,
            reply_markup=result_keyboard(results)
        )

    await callback.answer()
