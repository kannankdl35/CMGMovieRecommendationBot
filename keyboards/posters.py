# Location: keyboards/posters.py  (NEW FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboard for the "⬇️ DOWNLOAD POSTERS" feature (see keyboards/home.py for
# the main-menu entry point, plugins/inline.py for the inline search these
# buttons open, and plugins/callback.py's "posters_open" branch for what
# shows this page).
# ---------------------------------------------------------------------------

POSTERS_MENU_TEXT = (
    "⬇️ DOWNLOAD POSTERS\n\n"
    "Choose which type of posters you want to download ⬇️"
)


def posters_menu_keyboard():
    """Shown right after tapping "⬇️ DOWNLOAD POSTERS" on the main menu.

    Three options:
      - ↕️ Download Vertical Posters   -> opens the inline search with
                                          "vposters " pre-filled; results
                                          show (and download) portrait posters
      - ↔️ Download Horizontal Posters -> opens the inline search with
                                          "hposters " pre-filled; results
                                          show (and download) landscape posters
      - 🏠 Home                        -> back to the bot's main menu
                                          (callback_data "back_home", already
                                          handled in plugins/callback.py)

    The first two use Telegram Inline Mode exactly like the SEARCH buttons on
    the main menu - the "vposters " / "hposters " word at the start of the
    inline query is how plugins/inline.py's _parse_mode() tells which
    orientation was picked.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "↕️ Download Vertical Posters",
                    switch_inline_query_current_chat="vposters "
                )
            ],
            [
                InlineKeyboardButton(
                    "↔️ Download Horizontal Posters",
                    switch_inline_query_current_chat="hposters "
                )
            ],
            [InlineKeyboardButton("🏠 Home", callback_data="back_home")],
        ]
    )
