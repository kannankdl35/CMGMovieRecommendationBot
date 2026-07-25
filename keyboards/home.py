from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_keyboard():
    """The Home menu has four buttons:

      1. 🔍 SEARCH - IMDb
      2. 🔍 SEARCH - TMDb
      3. 🔥 TRENDING NOW
      4. 📋 WATCHLIST

    Both search buttons use Telegram Inline Mode, same as the old
    "Find Movies & Series" button - switch_inline_query_current_chat
    pre-fills "@<BotUsername> imdb " / "@<BotUsername> tmdb " into this
    chat's message box. The leading "imdb "/"tmdb " word is how
    plugins/inline.py's single inline-query handler tells which backend to
    search (services.imdb vs services.tmdb) - Telegram doesn't otherwise
    report which button was tapped, only the text the user ends up typing.

    ✅ NEW: "🔥 Trending Now" (callback_data="trending_open") - opens the
    Today / This Week / Home selection page (keyboards/trending.py),
    powered by TMDb's trending endpoints. Handled in plugins/callback.py.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔍 SEARCH - IMDb",
                    switch_inline_query_current_chat="imdb "
                )
            ],
            [
                InlineKeyboardButton(
                    "🔍 SEARCH - TMDb",
                    switch_inline_query_current_chat="tmdb "
                )
            ],
            [
                InlineKeyboardButton(
                    "🔥 Trending Now",
                    callback_data="trending_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 WATCHLIST",
                    callback_data="watchlist_open"
                )
            ]
        ]
    )
