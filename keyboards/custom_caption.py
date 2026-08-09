# Location: keyboards/custom_caption.py  (NEW FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboards for the ✅ NEW ✏️ Custom Caption feature - lives one level
# under IMDb Settings / TMDb Settings (see keyboards/settings.py's
# "✏️ Custom Caption" button). See database/settings_db.py for the saved
# template itself, utils/formatter.py's render_custom_caption() for how
# it's filled in, and plugins/custom_caption.py for the page text, the
# plain-text message handler that saves what the user sends, and the
# /show_custom_caption + /delete_custom_caption commands.
# ---------------------------------------------------------------------------


def custom_caption_keyboard(source):
    """Shown on the "✏️ Custom Caption" page itself (opened from IMDb/
    TMDb Settings, callback_data "custom_caption_imdb_open"/
    "custom_caption_tmdb_open" - see plugins/callback.py). Just one
    "⬅ Back" button, back to that same source's Settings page (NOT the
    Settings menu, and NOT the main menu) - callback_data
    "settings_imdb_open" / "settings_tmdb_open", already handled in
    plugins/callback.py. Tapping it also cancels "awaiting a custom
    caption message" mode, same as every other button (see the top of
    plugins/callback.py's callback_handler()).
    """
    back_target = "settings_imdb_open" if source == "imdb" else "settings_tmdb_open"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back", callback_data=back_target)]]
    )


def delete_custom_caption_keyboard():
    """Shown by the /delete_custom_caption command
    (plugins/custom_caption.py) only when the user has a saved template
    for BOTH IMDb and TMDb - lets them pick which one(s) to remove rather
    than guessing/deleting both by default. If only one source has a
    saved template, that command deletes it directly without showing
    this keyboard at all.
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎥 IMDb only", callback_data="delcap_imdb")],
            [InlineKeyboardButton("📽 TMDb only", callback_data="delcap_tmdb")],
            [InlineKeyboardButton("🗑 Both", callback_data="delcap_both")],
            [InlineKeyboardButton("✖ Cancel", callback_data="delcap_cancel")],
        ]
    )
