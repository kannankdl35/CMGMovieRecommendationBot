from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.genre import genre_keyboard


@Client.on_callback_query()
async def series_callback(client, callback: CallbackQuery):

    if callback.data == "series":

        await callback.message.edit_text(
            text="📺 **Select Series Genre**",
            reply_markup=genre_keyboard("series")
        )

        await callback.answer()
