from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboard for "🎲 Suggest Random Movie" (see keyboards/home.py for the
# main-menu entry point and plugins/callback.py for everything these
# buttons trigger).
#
# Flow: Home -> Language page -> tap a language -> one random movie's full
# details are sent straight away (poster + info + Watchlist/Search
# Another/Done), same details view as 🔥 Trending Now /
# 🎬 Upcoming Movies (plugins/details.py's send_trending_details()) - no
# intermediate numbered list.
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
#   - the 5 regional languages: rating >= 7, votes >= 50
#   - English / Korean: rating >= 7, votes >= 500
#   - Others: rating >= 7, votes >= 1000
LANGUAGE_FILTERS = {
    "malayalam": (7.0, 50),
    "tamil": (7.0, 50),
    "hindi": (7.0, 50),
    "kannada": (7.0, 50),
    "telugu": (7.0, 50),
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
