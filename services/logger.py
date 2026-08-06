# Location: services/logger.py  (NEW FILE)

from datetime import datetime

from config import LOG_CHANNEL_ID

# ---------------------------------------------------------------------------
# ✅ NEW - Activity Log Channel
#
# Sends two kinds of events to a private log channel/group (LOG_CHANNEL_ID
# in .env) that the bot has been made an admin of:
#   1. #NewUser       - the very first time someone starts the bot. Fired
#      from plugins/start.py, but only when database/users_db.py's
#      register_user() reports the user was just inserted (not just an
#      existing user re-running /start).
#   2. #BotRestarted  - once, every time the bot process boots up. Fired
#      from bot.py's main(), right after app.start().
#
# If LOG_CHANNEL_ID isn't set, both functions silently no-op so the bot
# still runs fine without a log channel configured. Any send failure (bot
# not actually an admin there, wrong chat id, etc.) is swallowed the same
# way - logging must never crash the bot or block a real user's /start.
# ---------------------------------------------------------------------------


async def send_new_user_log(client, user):
    """Notify the log channel about a brand-new user.

    `user` is a Pyrogram User object (message.from_user in
    plugins/start.py). The name is a clickable link to the user's profile
    via tg://user?id=... , which works even for users with no @username.
    """
    if not LOG_CHANNEL_ID:
        return

    user_id = user.id
    name = user.first_name or "Unknown"

    text = (
        "🆕 **#NewUser**\n\n"
        f"🆔 **ID -** `{user_id}`\n"
        f"👤 **Name -** [{name}](tg://user?id={user_id})"
    )

    if user.username:
        text += f"\n🔗 **Username -** @{user.username}"

    try:
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text,
            disable_web_page_preview=True,
        )
    except Exception as e:
        print("⚠️ Could not send new-user log (continuing anyway)")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")


async def send_bot_restart_log(client):
    """Notify the log channel that the bot process has (re)started."""
    if not LOG_CHANNEL_ID:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = (
        "🔄 **#BotRestarted**\n\n"
        "✅ **Status -** Online\n"
        f"🕒 **Time -** {now}"
    )

    try:
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text,
            disable_web_page_preview=True,
        )
    except Exception as e:
        print("⚠️ Could not send bot-restart log (continuing anyway)")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
