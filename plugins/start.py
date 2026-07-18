from pyrogram import Client, filters

# ✅ Reuse the shared home keyboard instead of duplicating buttons here
from keyboards.home import home_keyboard

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
        "Or use 🔍 **Find Movies** to search for a specific title.\n\n"
        "Click a button below to get started."
    )

    buttons = home_keyboard()

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
