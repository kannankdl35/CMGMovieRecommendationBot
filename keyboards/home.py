from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎥 Suggest Me",
                    callback_data="suggest_me"
                )
            ]
        ]
    )
