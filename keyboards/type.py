from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def type_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎬 Movies",
                    callback_data="movies"
                ),
                InlineKeyboardButton(
                    "📺 Series",
                    callback_data="series"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅ Back",
                    callback_data="back_home"
                )
            ]
        ]
    )
