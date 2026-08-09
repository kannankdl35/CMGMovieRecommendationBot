# Location: keyboards/about.py  (NEW FILE)

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
            [InlineKeyboardButton("⬅ Back", callback_data="back_home")],
        ]
    )
