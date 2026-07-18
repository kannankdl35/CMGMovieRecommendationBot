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
                # ✅ NEW: Feature 1 - Find Movies button
                InlineKeyboardButton(
                    "🔍 Find Movies",
                    callback_data="find_movies"
                )
            ]
        ]
    )
