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
        "👋 **Welcome to CMG Movie Recommendation Bot!**\n\n"
        "Discover movies & shows — posters, ratings, cast & plot, "
        "all in one tap.\n\n"
        "🔍 **Search** — IMDb or TMDb\n"
        "🔥 **Trending** — today & this week\n"
        "🎬 **Upcoming** — theatre & OTT releases\n"
        "🎲 **Random Pick** — a surprise, always 7★+\n"
        "📋 **Watchlist** — save what to watch\n"
        "📅 **This Month** — track & unlock achievements\n"
        "⚙️ **Settings** — customize your details\n\n"
        "👇 Tap a button below to begin"
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
