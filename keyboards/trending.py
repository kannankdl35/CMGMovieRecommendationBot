from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboards for the "🔥 Trending Now" feature (see keyboards/home.py for the
# main-menu entry point and plugins/callback.py for everything these
# buttons trigger).
# ---------------------------------------------------------------------------


def trending_menu_keyboard():
    """Shown right after tapping "🔥 Trending Now" on the main menu.

    Three options:
      - 📅 Today       -> TMDb's daily trending endpoint
      - 📈 This Week   -> TMDb's weekly trending endpoint
      - 🏠 Home        -> back to the bot's main menu (callback_data
                          "back_home", already handled in
                          plugins/callback.py)
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📅 Today", callback_data="trending_day")],
            [InlineKeyboardButton("📈 This Week", callback_data="trending_week")],
            [InlineKeyboardButton("🏠 Home", callback_data="back_home")],
        ]
    )


def trending_list_keyboard(count):
    """Numbered buttons (1..count) for the trending listing, 5 per row,
    plus a "⬅ Back" button.

    `count` is how many trending items are currently displayed (up to 10).
    Button `n`'s callback_data is "trend_sel_<n>" - plugins/callback.py
    looks up index `n` in the trending results this user last fetched
    (stored via database.user_state.save_trending_results /
    get_trending_results), the same pattern keyboards/watchlist.py uses to
    map its numbered buttons back to watchlist documents.

    "⬅ Back" (callback_data "trend_back") returns to the Today / This
    Week / Home selection page - NOT the main menu.
    """
    buttons = []
    row = []

    for index in range(1, count + 1):
        row.append(
            InlineKeyboardButton(str(index), callback_data=f"trend_sel_{index}")
        )

        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="trend_back")])

    return InlineKeyboardMarkup(buttons)
