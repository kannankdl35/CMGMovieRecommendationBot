from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎥 Suggest Me",
                    callback_data="suggest_me"
                )
            ],
            [
                # ✅ UPDATED: Feature 1 - Find Movies & Series now uses Telegram
                # Inline Mode instead of asking the user to type into the chat.
                # switch_inline_query_current_chat="" pre-fills
                # "@<BotUsername> " in this same chat's message box, so the
                # user can type a title and pick from live inline results
                # (handled in plugins/inline.py).
                InlineKeyboardButton(
                    "🔍 Find Movies & Series",
                    switch_inline_query_current_chat=""
                )
            ]
        ]
    )
