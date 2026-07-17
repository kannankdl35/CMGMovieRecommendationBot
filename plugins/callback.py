from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.type import type_keyboard
from keyboards.home import home_keyboard
from keyboards.genre import genre_keyboard


@Client.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):

    data = callback.data

    if data == "suggest_me":

        await callback.message.edit_text(
            text="🎬 **Select what you're looking for**",
            reply_markup=type_keyboard()
        )

    elif data == "movies":

        await callback.message.edit_text(
            text="🎬 **Select a Movie Genre**",
            reply_markup=genre_keyboard("movie")
        )

    elif data == "series":

        await callback.message.edit_text(
            text="📺 **Select a Series Genre**",
            reply_markup=genre_keyboard("series")
        )

    elif data == "back_home":

        await callback.message.edit_text(
            text=(
                "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
                "🎬 Discover Movies & TV Series based on:\n\n"
                "• 🎭 Genre\n"
                "• 🌍 Language\n"
                "• ⭐ Rating\n\n"
                "Click the button below to start."
            ),
            reply_markup=home_keyboard()
        )

    await callback.answer()
