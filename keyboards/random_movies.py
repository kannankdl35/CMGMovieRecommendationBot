from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboards for "🎲 Suggest Random Movie" (see keyboards/home.py for the
# main-menu entry point and plugins/callback.py for everything these
# buttons trigger).
#
# Flow: Home -> Language page -> numbered listing of random movies for that
# language -> full details page. Same category -> list -> details shape as
# 🔥 Trending Now (keyboards/trending.py) and 🎬 Upcoming Movies
# (keyboards/upcoming.py).
#
# "others" is a catch-all bucket (any language that isn't one of the other
# seven) rather than a single ISO language code - see
# services/tmdb.py's get_random_movies_other_languages().
# ---------------------------------------------------------------------------

LANGUAGE_LABELS = {
    "malayalam": "Malayalam",
    "tamil": "Tamil",
    "hindi": "Hindi",
    "kannada": "Kannada",
    "telugu": "Telugu",
    "english": "English",
    "korean": "Korean",
    "others": "Others",
}

LANGUAGE_ORDER = [
    "malayalam", "tamil", "hindi", "kannada", "telugu",
    "english", "korean", "others",
]

# ISO 639-1 codes TMDb's with_original_language filter expects, for the
# five regional-language buttons + English + Korean. "others" has no single
# code - handled separately in services/tmdb.py.
LANGUAGE_CODES = {
    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "kannada": "kn",
    "telugu": "te",
    "english": "en",
    "korean": "ko",
}

# Quality floor per bucket, per the feature spec:
#   - the 5 regional languages: rating >= 7, votes >= 100
#   - English / Korean: rating >= 7, votes >= 500
#   - Others: rating >= 7, votes >= 1000
LANGUAGE_FILTERS = {
    "malayalam": (7.0, 100),
    "tamil": (7.0, 100),
    "hindi": (7.0, 100),
    "kannada": (7.0, 100),
    "telugu": (7.0, 100),
    "english": (7.0, 500),
    "korean": (7.0, 500),
    "others": (7.0, 1000),
}


def random_language_keyboard():
    """Shown right after tapping "🎲 Suggest Random Movie" on the main
    menu. Two buttons per row, "🔙 Back" returns to the main menu.
    """
    rows = []
    row = []

    for lang in LANGUAGE_ORDER:
        row.append(
            InlineKeyboardButton(
                LANGUAGE_LABELS[lang], callback_data=f"random_lang_{lang}"
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])

    return InlineKeyboardMarkup(rows)


def random_list_keyboard(lang, count):
    """Numbered buttons (1..count) for a language's random-movie listing,
    5 per row, plus a "🔙 Back" button.

    Button `n`'s callback_data is "random_sel_<lang>_<n>" -
    plugins/callback.py looks up index `n` in the random results this user
    last fetched for that language (database/user_state.py).

    "🔙 Back" (callback_data "random_open") returns to the language page.
    """
    buttons = []
    row = []

    for index in range(1, count + 1):
        row.append(
            InlineKeyboardButton(str(index), callback_data=f"random_sel_{lang}_{index}")
        )
        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="random_open")])

    return InlineKeyboardMarkup(buttons)
