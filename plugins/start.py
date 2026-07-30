# Location: plugins/start.py  (REPLACE ENTIRE FILE)

from pyrogram import Client, filters

from keyboards.home import home_keyboard

# ✅ NEW - "This Month Watched" feature (Monthly Reset & Report): records
# this user so the end-of-month report knows to message them, even if
# their stats end up all zero for the month.
from database.users_db import register_user

print("✅ START PLUGIN LOADED")


@Client.on_message(filters.command("start"))
async def start_command(client, message):

    print("✅ /start COMMAND RECEIVED")

    user = message.from_user
    if user:
        await register_user(user.id, username=user.username, first_name=user.first_name)

    text = (
        "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
        "🎬 Find any Movie or TV Series and see its full details -\n"
        "poster, rating, cast, and plot.\n\n"
        "• 🔍 **SEARCH - IMDb** - search powered by IMDb\n"
        "• 🔍 **SEARCH - TMDb** - search powered by TMDb\n"
        "• 🔥 **TRENDING NOW** - what's trending today/this week on TMDb\n"
        "• 🎬 **UPCOMING MOVIES** - theatre & OTT releases by language\n"
        "• 🎲 **SUGGEST RANDOM MOVIE** - a random pick, 7+ rated with 500+ votes\n"
        "• 📋 **WATCHLIST** - your saved titles\n"
        "• 🗓️ **THIS MONTH WATCHED** - track what you've watched this month "
        "+ unlock achievements\n\n"
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
