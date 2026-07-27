from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboards for "🎬 Upcoming Movies" (see keyboards/home.py for the
# main-menu entry point and plugins/callback.py for everything these
# buttons trigger).
#
# Both branches - Theatre Release and OTT Release This Week - share this
# exact same category -> language -> numbered-list -> details workflow;
# only the underlying data source differs (services.theatre_releases vs
# services.ott_releases - see plugins/callback.py).
# ---------------------------------------------------------------------------

LANGUAGE_LABELS = {
    "malayalam": "Malayalam",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "kannada": "Kannada",
    "hindi": "Hindi",
    "english": "English",
}

LANGUAGE_ORDER = ["malayalam", "tamil", "telugu", "kannada", "hindi", "english"]


def upcoming_category_keyboard():
    """Shown right after tapping "🎬 Upcoming Movies" on the main menu."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎬 Theatre Release", callback_data="upcoming_cat_theatre")],
            [InlineKeyboardButton("📺 OTT Release This Week", callback_data="upcoming_cat_ott")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
        ]
    )


def upcoming_language_keyboard(category):
    """Shown after picking Theatre Release or OTT Release This Week.
    `category` is "theatre" or "ott" - baked into each button's
    callback_data ("upcoming_lang_<category>_<language>") so
    plugins/callback.py knows which data source to use once a language is
    picked. "🔙 Back" (callback_data "upcoming_open") returns to the
    category menu above.
    """
    rows = []
    row = []

    for lang in LANGUAGE_ORDER:
        row.append(
            InlineKeyboardButton(
                LANGUAGE_LABELS[lang], callback_data=f"upcoming_lang_{category}_{lang}"
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="upcoming_open")])

    return InlineKeyboardMarkup(rows)


def upcoming_list_keyboard(category, lang, count):
    """Numbered buttons (1..count) for a category+language's release
    listing, 5 per row, plus a "🔙 Back" button.

    Button `n`'s callback_data is "upcoming_sel_<category>_<lang>_<n>" -
    plugins/callback.py looks up index `n` in that category+language's
    cached release list.

    "🔙 Back" returns to the language menu for the SAME category
    (callback_data "upcoming_cat_<category>" - the same callback_data used
    to first open that language menu, so one handler in
    plugins/callback.py covers both).
    """
    buttons = []
    row = []

    for index in range(1, count + 1):
        row.append(
            InlineKeyboardButton(
                str(index), callback_data=f"upcoming_sel_{category}_{lang}_{index}"
            )
        )
        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"upcoming_cat_{category}")])

    return InlineKeyboardMarkup(buttons)
