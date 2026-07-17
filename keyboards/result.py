from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def result_keyboard(results, page=1):

    PER_PAGE = 10

    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE

    page_results = results[start:end]

    buttons = []

    row = []

    for index, movie in enumerate(page_results, start=start + 1):

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

    navigation = []

    if page > 1:
        navigation.append(
            InlineKeyboardButton(
                "⬅ Previous",
                callback_data=f"page_{page - 1}"
            )
        )

    if end < len(results):
        navigation.append(
            InlineKeyboardButton(
                "➡ Next",
                callback_data=f"page_{page + 1}"
            )
        )

    if navigation:
        buttons.append(navigation)

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="back_home"
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)
