from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import WEBAPP_URL

# ✅ Feature 4 - User Watchlist
# ✅ CHANGED: The watchlist now opens as a Telegram Mini App (Web App)
# instead of dumping one message/photo per saved title into the chat.
# Tapping the button below launches webapp/index.html, which fetches the
# user's saved titles from webapp_server.py and renders them as cards with
# Delete / Share actions - all inside a single scrollable screen.


@Client.on_message(filters.command("watchlist"))
async def watchlist_command(client, message):
    """Entry point for /watchlist - opens the Watchlist Mini App."""
    text = (
        "📋 **Your Personal Watchlist**\n\n"
        "Movies and series you've saved show up here.\n"
        "Tap the button below to view, delete, or share them."
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 View My WatchList",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )

    await message.reply_text(text, reply_markup=buttons)
