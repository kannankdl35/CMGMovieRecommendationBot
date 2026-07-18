from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.user_state import set_state, get_state
from services.omdb import search_titles
from utils.ui import send_result_cards

# ✅ Feature 1 - Find Movies
# Limit how many results we send as cards to keep the chat readable
SEARCH_RESULT_LIMIT = 8


@Client.on_message(
    filters.private
    & filters.text
    & ~filters.command(["start", "watchlist"])
)
async def search_text_handler(client, message):
    """Handle the movie/series name typed by the user after pressing
    🔍 Find Movies. Ignored unless the user is currently in search mode,
    so this never interferes with any other existing feature.
    """
    user_id = message.from_user.id
    state = get_state(user_id)

    if not state.get("awaiting_search"):
        return  # Not in search mode - leave the message alone

    query = message.text.strip()

    # Consume the search mode so a second message isn't treated as a new query
    set_state(user_id, "awaiting_search", False)

    if not query:
        await message.reply_text("Please type a valid movie or series name.")
        return

    results = search_titles(query)

    if not results:
        await message.reply_text(
            f"❌ No results found for **{query}**.\n\n"
            "Try another title, or press /start to go back."
        )
        return

    results = results[:SEARCH_RESULT_LIMIT]

    await message.reply_text(f"🔎 Results for **{query}**:")

    await send_result_cards(client, message.chat.id, results, "sr_")
