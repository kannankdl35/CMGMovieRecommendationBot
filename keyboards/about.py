# Location: keyboards/about.py  (REPLACE ENTIRE FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from about.about_info import REPORT_USERNAME


def about_keyboard():
    """Shown under the "ℹ️ About" text (plugins/callback.py's "about_open"
    handler; the text itself is built by about/about_info.py's
    build_about_text()).

      - 🐞 Report Issues/Bugs -> a URL button (not callback_data) that
                                  opens a chat with REPORT_USERNAME
                                  (about/about_info.py) directly - no
                                  round-trip through the bot needed.
      - ❓ Help                -> ✅ NEW - opens the full feature guide
                                  (callback_data "help_open", handled in
                                  plugins/callback.py; text built by
                                  about/about_info.py's build_help_text()).
      - ⬅ Back                -> back to the bot's main menu
                                  (callback_data "back_home", already
                                  handled in plugins/callback.py)
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🐞 Report Issues/Bugs",
                    url=f"https://t.me/{REPORT_USERNAME}"
                )
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help_open")],
            [InlineKeyboardButton("⬅ Back", callback_data="back_home")],
        ]
    )


# ✅ NEW - ❓ Help feature
def help_keyboard():
    """Shown under the "❓ Help" text (plugins/callback.py's "help_open"
    handler; the text itself is built by about/about_info.py's
    build_help_text()).

      - ⬅ Back -> back to the "ℹ️ About" page (callback_data "about_open",
                   already handled in plugins/callback.py) - NOT the main
                   menu, since Help was opened from About.
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⬅ Back", callback_data="about_open")],
        ]
    )
