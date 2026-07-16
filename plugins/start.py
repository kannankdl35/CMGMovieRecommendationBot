from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

print("✅ START PLUGIN LOADED")


@Client.on_message(filters.command("start"))
async def start_command(client, message):

    print("✅ /start COMMAND RECEIVED")

    text = (
        "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
        "🎬 Discover Movies & TV Series based on:\n\n"
        "• 🎭 Genre\n"
        "• 🌍 Language\n"
        "• ⭐ IMDb Rating\n\n"
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

    try:
        await message.reply_text(
            text=text,
            reply_markup=buttons,
            disable_web_page_preview=True
        )

        print("✅ Reply sent successfully")

    except Exception as e:
        print("❌ ERROR SENDING REPLY")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
