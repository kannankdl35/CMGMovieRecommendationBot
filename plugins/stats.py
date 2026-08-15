# Location: plugins/stats.py  (NEW FILE)

from pyrogram import Client, filters

from config import ADMIN_IDS, MONGO_STORAGE_LIMIT_MB
from database.stats_db import (
    get_total_users,
    get_new_users_today,
    get_total_searches,
    get_storage_stats,
)

print("✅ STATS PLUGIN LOADED")


@Client.on_message(filters.command("stats"))
async def stats_command(client, message):
    """/stats - Total Users, New Users Today, Total Searches, Used/Free
    Storage. See database/stats_db.py for how each number is computed.

    Restricted to config.ADMIN_IDS if that's set in .env; if it's left
    empty, /stats is open to any user (see config.py).
    """
    user = message.from_user

    if ADMIN_IDS and (not user or user.id not in ADMIN_IDS):
        await message.reply_text("❌ You're not authorized to use this command.")
        return

    try:
        total_users = await get_total_users()
        new_users_today = await get_new_users_today()
        total_searches = await get_total_searches()
        used_mb, free_mb = await get_storage_stats(MONGO_STORAGE_LIMIT_MB)
    except Exception as e:
        print("⚠️ /stats failed (continuing anyway)")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        await message.reply_text("⚠️ Couldn't fetch stats right now. Please try again.")
        return

    text = (
        "📊 **Bot Stats**\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"🆕 **New Today:** {new_users_today}\n"
        f"🔍 **Total Searches:** {total_searches}\n"
        f"💾 **Used Storage:** {used_mb:.2f} MB\n"
        f"📦 **Free Storage:** {free_mb:.2f} MB"
    )

    await message.reply_text(text)
