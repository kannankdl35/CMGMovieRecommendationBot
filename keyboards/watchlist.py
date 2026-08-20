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

    # ✅ NEW: "🗑 DELETE THE FULL LIST" - only shown when there's something
    # to delete. Tapping it does NOT delete anything by itself - it opens
    # a Yes/Cancel confirmation prompt (see watchlist_confirm_delete_keyboard()
    # below), handled by the "wldelall_confirm" / "wldelall_yes" /
    # "wldelall_cancel" callbacks in plugins/callback.py.
    if docs:
        buttons.append(
            [InlineKeyboardButton("🗑 DELETE THE FULL LIST", callback_data="wldelall_confirm")]
        )

    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="back_home")])

    return InlineKeyboardMarkup(buttons)


# ✅ NEW: Shown after tapping "🗑 DELETE THE FULL LIST" - asks the user to
# confirm before the whole watchlist is wiped. "✅ Yes" -> "wldelall_yes",
# "❌ Cancel" -> "wldelall_cancel" (both handled in plugins/callback.py).
def watchlist_confirm_delete_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes", callback_data="wldelall_yes")],
            [InlineKeyboardButton("❌ Cancel", callback_data="wldelall_cancel")],
        ]
    )
