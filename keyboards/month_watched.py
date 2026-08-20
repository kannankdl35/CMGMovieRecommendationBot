# Location: keyboards/month_watched.py  (NEW FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboards for "🗓️ This Month Watched" (see keyboards/home.py for the
# main-menu entry point and plugins/callback.py for everything these
# buttons trigger). Same numbered-list pattern as keyboards/watchlist.py.
# ---------------------------------------------------------------------------


def month_watched_list_keyboard(docs):
    """Numbered buttons (docs[0] -> "1", docs[1] -> "2", ...) for the This
    Month Watched listing, 5 per row.

    Each button's callback_data is "mw_<imdb_id>" - handled in
    plugins/callback.py the same way keyboards/watchlist.py's "wl_" buttons
    are: tapping it opens that title's normal details page (poster + full
    info + Watchlist / This Month Watched / Search Another / Done buttons).

    Below the numbers:
      - "🗑 DELETE THE FULL LIST" (callback_data "mwdelall_confirm", only
        shown when there's something to delete)
      - "🏆 See the Achievements" (callback_data "mw_achievements")
      - "⬅️ Back" (callback_data "back_home" - this listing is a plain
        text message, same as the Home menu itself, so the existing
        back_home handler in plugins/callback.py already works here
        unmodified).
    """
    buttons = []
    row = []

    for index, doc in enumerate(docs, start=1):
        imdb_id = doc.get("imdb_id")

        if not imdb_id:
            continue

        row.append(
            InlineKeyboardButton(str(index), callback_data=f"mw_{imdb_id}")
        )

        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # ✅ NEW: "🗑 DELETE THE FULL LIST" - only shown when there's something
    # to delete. Tapping it does NOT delete anything by itself - it opens
    # a Yes/Cancel confirmation prompt (see
    # month_watched_confirm_delete_keyboard() below), handled by the
    # "mwdelall_confirm" / "mwdelall_yes" / "mwdelall_cancel" callbacks in
    # plugins/callback.py.
    if docs:
        buttons.append(
            [InlineKeyboardButton("🗑 DELETE THE FULL LIST", callback_data="mwdelall_confirm")]
        )

    buttons.append(
        [InlineKeyboardButton("🏆 SEE THE ACHIEVEMENTS", callback_data="mw_achievements")]
    )
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back_home")])

    return InlineKeyboardMarkup(buttons)


# ✅ NEW: Shown after tapping "🗑 DELETE THE FULL LIST" - asks the user to
# confirm before the whole This Month Watched list is wiped. "✅ Yes" ->
# "mwdelall_yes", "❌ Cancel" -> "mwdelall_cancel" (both handled in
# plugins/callback.py).
def month_watched_confirm_delete_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes", callback_data="mwdelall_yes")],
            [InlineKeyboardButton("❌ Cancel", callback_data="mwdelall_cancel")],
        ]
    )


def achievements_keyboard():
    """Shown on the "🏆 See the Achievements" page. "⬅️ Back" returns to
    the This Month Watched listing (callback_data "mw_achievements_back") -
    NOT the main menu."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ BACK", callback_data="mw_achievements_back")]]
    )
