from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def language_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
                InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hi"),
            ],
            [
                InlineKeyboardButton("🌴 Malayalam", callback_data="lang_ml"),
                InlineKeyboardButton("🎬 Tamil", callback_data="lang_ta"),
            ],
            [
                InlineKeyboardButton("🔥 Telugu", callback_data="lang_te"),
                InlineKeyboardButton("🌿 Kannada", callback_data="lang_kn"),
            ],
            [
                InlineKeyboardButton("🌸 Japanese", callback_data="lang_ja"),
                InlineKeyboardButton("🎭 Korean", callback_data="lang_ko"),
            ],
            [
                InlineKeyboardButton("🐉 Chinese", callback_data="lang_zh"),
                InlineKeyboardButton("💃 Spanish", callback_data="lang_es"),
            ],
            [
                InlineKeyboardButton("🥖 French", callback_data="lang_fr"),
                InlineKeyboardButton("🍝 Italian", callback_data="lang_it"),
            ],
            [
                InlineKeyboardButton("🇩🇪 German", callback_data="lang_de"),
                InlineKeyboardButton("🇷🇺 Russian", callback_data="lang_ru"),
            ],
            [
                InlineKeyboardButton("⬅ Back", callback_data="movies"),
                InlineKeyboardButton("🏠 Home", callback_data="back_home"),
            ]
        ]
    )
