from pyrogram import Client, filters

from database.watchlist_db import get_watchlist
from keyboards.watchlist import watchlist_keyboard

# ✅ CHANGED: Feature 4 - User Watchlist now works completely INSIDE the
# Telegram chat. The old Telegram Mini App / Web App (webapp/,
# webapp_server.py, utils/webapp_auth.py) has been removed entirely.
#
# Tapping "📋 Watchlist" on the Home menu (callback_data="watchlist_open",
# handled in plugins/callback.py) or sending /watchlist prints the user's
# saved titles as a single numbered text message, with matching numbered
# inline buttons underneath (keyboards/watchlist.py). Tapping a number
# button shows that title's full details page - the exact same details
# view used when a user searches for a movie/series (services/omdb.py +
# utils/formatter.py via plugins/details.py's send_omdb_details), rendered
# with a native Telegram message/photo. No Web App or external page is ever
# opened.

WATCHLIST_DISPLAY_LIMIT = 30  # keeps the text + button grid well within Telegram's limits


def build_watchlist_text(docs):
    """Build the numbered watchlist message body for the given (already
    limited/ordered) list of watchlist documents."""
    if not docs:
        return (
            "📭 Your watchlist is empty.\n\n"
            "Use 🔍 **Find Movies & Series** to search for a title, then tap "
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


@Client.on_message(filters.command("watchlist"))
async def watchlist_command(client, message):
    """Entry point for /watchlist - lists saved titles as numbered text with
    numbered inline buttons underneath, fully inside the Telegram chat."""
    text, keyboard = await get_watchlist_view(message.from_user.id)

    await message.reply_text(text, reply_markup=keyboard)
