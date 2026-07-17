from pyrogram import Client
from pyrogram.types import CallbackQuery


@Client.on_callback_query()
async def movie_callback(client: Client, callback: CallbackQuery):

    print("=" * 40)
    print("MOVIE CALLBACK RECEIVED")
    print("DATA:", callback.data)
    print("=" * 40)

    await callback.answer("Movie callback reached!")
