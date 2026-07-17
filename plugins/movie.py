from pyrogram import Client
from pyrogram.types import CallbackQuery

print("✅ MOVIE PLUGIN LOADED")


@Client.on_callback_query()
async def movie_callback(client: Client, callback: CallbackQuery):

    print("MOVIE CALLBACK:", callback.data)

    await callback.answer("Movie callback reached!")
