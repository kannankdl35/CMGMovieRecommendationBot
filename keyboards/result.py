from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def result_keyboard(page=1):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 More Results",
                    callback_data=f"page_{page + 1}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="back_home"
                )
            ]
        ]
    )
