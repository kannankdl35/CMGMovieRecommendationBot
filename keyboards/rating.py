from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def rating_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⭐ 9+", callback_data="rating_9"),
                InlineKeyboardButton("⭐ 8+", callback_data="rating_8"),
            ],
            [
                InlineKeyboardButton("⭐ 7+", callback_data="rating_7"),
                InlineKeyboardButton("⭐ 6+", callback_data="rating_6"),
            ],
            [
                InlineKeyboardButton("⭐ 5+", callback_data="rating_5"),
                InlineKeyboardButton("⭐ 4+", callback_data="rating_4"),
            ],
            [
                InlineKeyboardButton("⭐ 3+", callback_data="rating_3"),
                InlineKeyboardButton("⭐ 2+", callback_data="rating_2"),
            ],
            [
                InlineKeyboardButton("⭐ 1+", callback_data="rating_1"),
            ],
            [
                InlineKeyboardButton("⬅ Back", callback_data="back_language"),
                InlineKeyboardButton("🏠 Home", callback_data="back_home"),
            ]
        ]
    )
