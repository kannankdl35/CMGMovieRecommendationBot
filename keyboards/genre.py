from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def genre_keyboard(movie_type: str):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 Action", callback_data=f"{movie_type}_action"),
                InlineKeyboardButton("🌍 Adventure", callback_data=f"{movie_type}_adventure"),
            ],
            [
                InlineKeyboardButton("🎞 Animation", callback_data=f"{movie_type}_animation"),
                InlineKeyboardButton("😂 Comedy", callback_data=f"{movie_type}_comedy"),
            ],
            [
                InlineKeyboardButton("🕵 Crime", callback_data=f"{movie_type}_crime"),
                InlineKeyboardButton("📖 Documentary", callback_data=f"{movie_type}_documentary"),
            ],
            [
                InlineKeyboardButton("🎭 Drama", callback_data=f"{movie_type}_drama"),
                InlineKeyboardButton("👨‍👩‍👧 Family", callback_data=f"{movie_type}_family"),
            ],
            [
                InlineKeyboardButton("✨ Fantasy", callback_data=f"{movie_type}_fantasy"),
                InlineKeyboardButton("📜 History", callback_data=f"{movie_type}_history"),
            ],
            [
                InlineKeyboardButton("😱 Horror", callback_data=f"{movie_type}_horror"),
                InlineKeyboardButton("🎵 Music", callback_data=f"{movie_type}_music"),
            ],
            [
                InlineKeyboardButton("🕵 Mystery", callback_data=f"{movie_type}_mystery"),
                InlineKeyboardButton("❤️ Romance", callback_data=f"{movie_type}_romance"),
            ],
            [
                InlineKeyboardButton("🚀 Sci-Fi", callback_data=f"{movie_type}_scifi"),
                InlineKeyboardButton("📺 TV Movie", callback_data=f"{movie_type}_tvmovie"),
            ],
            [
                InlineKeyboardButton("🎯 Thriller", callback_data=f"{movie_type}_thriller"),
                InlineKeyboardButton("⚔ War", callback_data=f"{movie_type}_war"),
            ],
            [
                InlineKeyboardButton("🤠 Western", callback_data=f"{movie_type}_western"),
            ],
            [
                InlineKeyboardButton("⬅ Back", callback_data="suggest_me"),
                InlineKeyboardButton("🏠 Home", callback_data="back_home"),
            ]
        ]
    )
