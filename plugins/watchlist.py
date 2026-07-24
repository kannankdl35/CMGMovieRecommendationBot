from pyrogram import Client, filters

from database.watchlist_db import get_watchlist
from keyboards.watchlist import watchlist_keyboard

# ✅ Tracks the last watchlist listing message per user so it can be
# deleted before a new one is sent, avoiding duplicate stacked messages
# whenever the watchlist is refreshed.
from database.user_state import (
    set_last_watchlist_message,
    get_last_watchlist_message,
)

# The User Watchlist works completely INSIDE the Telegram chat - no Web
# App / Mini App page involved.
#
# Tapping "📋 WATCHLIST" on the Home menu (callback_data="watchlist_open",
# handled in plugins/callback.py) or sending /watchlist prints the user's
# saved titles as a single numbered text message, with matching numbered
# inline buttons underneath (keyboards/watchlist.py). Tapping a number
# button shows that title's full details page - the exact same details
# view used for a search result (plugins/details.py's send_imdb_details),
# rendered with a native Telegram message/photo. No Web App or external
# page is ever opened.

WATCHLIST_DISPLAY_LIMIT = 30  # keeps the text + button grid well within Telegram's limits


def build_watchlist_text(docs):
    """Build the numbered watchlist message body for the given (already
    limited/ordered) list of watchlist documents."""
    if not docs:
        return (
            "📭 Your watchlist is empty.\n\n"
            "Use 🔍 **SEARCH - IMDb** or 🔍 **SEARCH - TMDb** to find a title, then tap "
            "❤️ **Add to Watchlist** on its details page to save it here."
        )

    lines = ["📋 **Your Personal Watchlist**\n"]

    for index, doc in enumerate(docs, start=1):
        title = doc.get("title") or "Unknown"
        year = doc.get("year") or "-"
        media_type = doc.get("media_type", "movie")
        icon = "📺" if media_type == "series" else "🎬"

        lines.append(f"{index}. {icon} {title} ({year})")

    lines.append("\nTap a number below to see full details 👇")

    return "\n".join(lines)


async def get_watchlist_view(user_id):
    """Return (text, keyboard) for this user's current watchlist listing.

    Shared by the /watchlist command below and the "watchlist_open"
    callback (Home menu 📋 Watchlist button), handled in plugins/callback.py.
    """
    docs = await get_watchlist(user_id)
    docs = docs[:WATCHLIST_DISPLAY_LIMIT]

    text = build_watchlist_text(docs)
    keyboard = watchlist_keyboard(docs)

    return text, keyboard


async def send_watchlist_view(client, chat_id, user_id):
    """Delete the user's previous watchlist listing message (if any) and
    send a fresh one, remembering its message_id for next time.

    Fixes duplicate watchlist messages piling up in the chat - every time
    the watchlist changes (an item is deleted, or /watchlist is run again)
    the old listing message is removed first instead of a new one being
    appended underneath it.
    """
    text, keyboard = await get_watchlist_view(user_id)

    previous = get_last_watchlist_message(user_id)
    if previous:
        prev_chat_id, prev_message_id = previous
        try:
            await client.delete_messages(prev_chat_id, prev_message_id)
        except Exception:
            pass

    sent = await client.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    set_last_watchlist_message(user_id, chat_id, sent.id)

    return sent


@Client.on_message(filters.command("watchlist"))
async def watchlist_command(client, message):
    """Entry point for /watchlist - lists saved titles as numbered text with
    numbered inline buttons underneath, fully inside the Telegram chat.

    Deletes the previous watchlist listing message (if the user already
    had one open) before sending the refreshed one, so re-running
    /watchlist never leaves duplicate listings stacked in the chat.
    """
    user_id = message.from_user.id

    await send_watchlist_view(client, message.chat.id, user_id)
