from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.genre import genre_keyboard


@Client.on_callback_query()
async def movie_callback(client, callback: CallbackQuery):

    if callback.data == "movies":

        await callback.message.edit_text(
            text="🎬 **Select Movie Genre**",
            reply_markup=genre_keyboard("movie")
        )

        await callback.answer()
