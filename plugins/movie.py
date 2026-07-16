from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.genre import genre_keyboard
from keyboards.language import language_keyboard
from database.user_state import set_state


@Client.on_callback_query()
async def movie_callback(client: Client, callback: CallbackQuery):

    data = callback.data

    # Movie button
    if data == "movies":

        set_state(callback.from_user.id, "type", "movie")

        await callback.message.edit_text(
            "🎬 **Select Movie Genre**",
            reply_markup=genre_keyboard("movie")
        )

    # Movie Genre
    elif data.startswith("movie_"):

        genre = data.replace("movie_", "")

        set_state(callback.from_user.id, "genre", genre)

        await callback.message.edit_text(
            "🌍 **Select Language**",
            reply_markup=language_keyboard()
        )

    await callback.answer()
