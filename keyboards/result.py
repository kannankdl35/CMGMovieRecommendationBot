from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def result_keyboard(results, page=1):

    buttons = []

    row = []

    for index, movie in enumerate(results[:10], start=1):

        row.append(
            InlineKeyboardButton(
                str(index),
                callback_data=f"movie_{movie['id']}"
            )
        )

        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                "🔄 More Results",
                callback_data=f"page_{page + 1}"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="back_home"
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)
