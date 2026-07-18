from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ✅ Feature 4 - User Watchlist


@Client.on_message(filters.command("watchlist"))
async def watchlist_command(client, message):
    """Entry point for /watchlist - shows a button to open the saved list."""
    text = (
        "📋 **Your Personal Watchlist**\n\n"
        "Movies and series you've saved show up here.\n"
        "Tap the button below to view them."
    )

    buttons = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 My Watchlist", callback_data="wl_open")]]
    )

    await message.reply_text(text, reply_markup=buttons)
