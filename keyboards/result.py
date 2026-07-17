from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def result_keyboard(results, page=1):

    # Show only first 10 movies, no pagination
    PER_PAGE = 10
    page_results = results[:PER_PAGE]  # ✅ Take only first 10

    buttons = []
    row = []

    for index, movie in enumerate(page_results, start=1):  # Start from 1
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

    # ✅ REMOVED: No pagination buttons anymore
    # Add Home button only (no pagination buttons)
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="back_home")])

    return InlineKeyboardMarkup(buttons)
