from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def watchlist_keyboard(docs):
    """Build the numbered inline keyboard shown under the watchlist listing.

    `docs` is the (already-limited, already-ordered) list of watchlist
    documents being displayed as text - button "1" corresponds to docs[0],
    "2" to docs[1], and so on, matching the numbers printed in the message.

    Each button's callback_data is "wl_<imdb_id>", which is already handled
    in plugins/callback.py: tapping it renders the full details page for
    that title (poster + rating/genres/plot/etc, same as a Find Movies
    search result) directly in the chat - no Web App involved.
    """
    buttons = []
    row = []

    for index, doc in enumerate(docs, start=1):
        imdb_id = doc.get("imdb_id")

        if not imdb_id:
            continue

        row.append(
            InlineKeyboardButton(str(index), callback_data=f"wl_{imdb_id}")
        )

        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="back_home")])

    return InlineKeyboardMarkup(buttons)
