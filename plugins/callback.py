from pyrogram import Client
from pyrogram.types import CallbackQuery

from keyboards.type import type_keyboard
from keyboards.home import home_keyboard


@Client.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):

    if callback.data == "suggest_me":

        await callback.message.edit_text(
            text="🎬 **Select what you're looking for**",
            reply_markup=type_keyboard()
        )

    elif callback.data == "back_home":

        await callback.message.edit_text(
            text=(
                "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
                "🎬 Discover Movies & TV Series based on:\n"
                "• 🎭 Genre\n"
                "• 🌍 Language\n"
                "• ⭐ Rating\n\n"
                "Click the button below to start."
            ),
            reply_markup=home_keyboard()
        )

    await callback.answer()
