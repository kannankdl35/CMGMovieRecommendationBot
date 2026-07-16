from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def language_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data="language_en"
                ),
                InlineKeyboardButton(
                    "🇮🇳 Hindi",
                    callback_data="language_hi"
                )
            ],
            [
                InlineKeyboardButton(
                    "🌴 Malayalam",
                    callback_data="language_ml"
                ),
                InlineKeyboardButton(
                    "🎬 Tamil",
                    callback_data="language_ta"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔥 Telugu",
                    callback_data="language_te"
                ),
                InlineKeyboardButton(
                    "🌿 Kannada",
                    callback_data="language_kn"
                )
            ],
            [
                InlineKeyboardButton(
                    "🌸 Japanese",
                    callback_data="language_ja"
                ),
                InlineKeyboardButton(
                    "🎭 Korean",
                    callback_data="language_ko"
                )
            ],
            [
                InlineKeyboardButton(
                    "🐉 Chinese",
                    callback_data="language_zh"
                ),
                InlineKeyboardButton(
                    "💃 Spanish",
                    callback_data="language_es"
                )
            ],
            [
                InlineKeyboardButton(
                    "🥖 French",
                    callback_data="language_fr"
                ),
                InlineKeyboardButton(
                    "🍝 Italian",
                    callback_data="language_it"
                )
            ],
            [
                InlineKeyboardButton(
                    "🇩🇪 German",
                    callback_data="language_de"
                ),
                InlineKeyboardButton(
                    "🇷🇺 Russian",
                    callback_data="language_ru"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅ Back",
                    callback_data="movies"
                ),
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="back_home"
                )
            ]
        ]
    )
