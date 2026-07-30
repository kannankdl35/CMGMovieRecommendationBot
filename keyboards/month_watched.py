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

    buttons.append(
        [InlineKeyboardButton("🏆 See the Achievements", callback_data="mw_achievements")]
    )
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back_home")])

    return InlineKeyboardMarkup(buttons)


def achievements_keyboard():
    """Shown on the "🏆 See the Achievements" page. "⬅️ Back" returns to
    the This Month Watched listing (callback_data "mw_achievements_back") -
    NOT the main menu."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Back", callback_data="mw_achievements_back")]]
    )
