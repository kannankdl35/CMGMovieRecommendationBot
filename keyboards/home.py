from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_keyboard():
    """✅ CHANGED: "Suggest Me" is gone. The Home menu now has exactly three
    buttons:

      1. 🔍 SEARCH - IMDb
      2. 🔍 SEARCH - TMDb
      3. 📋 WATCHLIST

    Both search buttons use Telegram Inline Mode, same as the old
    "Find Movies & Series" button - switch_inline_query_current_chat
    pre-fills "@<BotUsername> imdb " / "@<BotUsername> tmdb " into this
    chat's message box. The leading "imdb "/"tmdb " word is how
    plugins/inline.py's single inline-query handler tells which backend to
    search (services.imdb vs services.tmdb) - Telegram doesn't otherwise
    report which button was tapped, only the text the user ends up typing.
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
                    "📋 WATCHLIST",
                    callback_data="watchlist_open"
                )
            ]
        ]
    )
