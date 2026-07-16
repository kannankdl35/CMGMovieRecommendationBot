from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@Client.on_message(filters.command("start"))
async def start_command(client, message):

    text = (
        "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
        "🎬 Discover Movies & TV Series based on:\n\n"
        "• 🎭 Genre\n"
        "• 🌍 Language\n"
        "• ⭐ Rating\n\n"
        "Click the button below to start discovering your next favorite movie."
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎥 Suggest Me",
                    callback_data="suggest_me"
                )
            ]
        ]
    )

    await message.reply_text(
        text=text,
        reply_markup=buttons,
        disable_web_page_preview=True
    )
