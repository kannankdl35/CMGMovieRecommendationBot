# Location: plugins/start.py  (REPLACE ENTIRE FILE)

from pyrogram import Client, filters

from keyboards.home import home_keyboard
from database.users_db import register_user
from services.logger import send_new_user_log

print("✅ START PLUGIN LOADED")


@Client.on_message(filters.command("start"))
async def start_command(client, message):

    print("✅ /start COMMAND RECEIVED")

    user = message.from_user
    if user:
        try:
            is_new_user = await register_user(
                user.id, username=user.username, first_name=user.first_name
            )
            if is_new_user:
                # ✅ NEW - Activity Log Channel: log only the FIRST /start
                # from this user, not every subsequent one.
                await send_new_user_log(client, user)
        except Exception as e:
            print("⚠️ Could not register user (continuing anyway)")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {e}")

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
        "+ unlock achievements\n"
        "• ⚙️ **SETTINGS** - choose which fields appear in your details\n\n"
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
