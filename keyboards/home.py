from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_keyboard():
    """The Home menu has six buttons:

      1. 🔍 SEARCH - IMDb
      2. 🔍 SEARCH - TMDb
      3. 🔥 TRENDING NOW
      4. 🎬 UPCOMING MOVIES
      5. 🎲 SUGGEST RANDOM MOVIE
      6. 📋 WATCHLIST

    Both search buttons use Telegram Inline Mode, same as the old
    "Find Movies & Series" button - switch_inline_query_current_chat
    pre-fills "@<BotUsername> imdb " / "@<BotUsername> tmdb " into this
    chat's message box. The leading "imdb "/"tmdb " word is how
    plugins/inline.py's single inline-query handler tells which backend to
    search (services.imdb vs services.tmdb) - Telegram doesn't otherwise
    report which button was tapped, only the text the user ends up typing.

    "🔥 Trending Now" (callback_data="trending_open") opens the
    Today / This Week / Home selection page (keyboards/trending.py),
    powered by TMDb's trending endpoints.

    "🎬 Upcoming Movies" (callback_data="upcoming_open") opens a
    Theatre Release / OTT Release This Week / Back selection page
    (keyboards/upcoming.py), each leading to a language picker
    (Malayalam/Tamil/Telugu/Kannada/Hindi/English) and then a numbered
    release list - see services/theatre_releases.py,
    services/ott_releases.py, and plugins/callback.py.

    ✅ NEW: "🎲 Suggest Random Movie" (callback_data="random_movie") picks
    one random movie from TMDb with a 7+ rating from at least 500 votes
    (services.tmdb.get_random_movie()) and shows its full details page
    immediately - no submenu, one tap and done. Handled in
    plugins/callback.py.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔍 SEARCH - IMDb",
                    switch_inline_query_current_chat="imdb "
                )
            ],
            [
                InlineKeyboardButton(
                    "🔍 SEARCH - TMDb",
                    switch_inline_query_current_chat="tmdb "
                )
            ],
            [
                InlineKeyboardButton(
                    "🔥 Trending Now",
                    callback_data="trending_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎬 Upcoming Movies",
                    callback_data="upcoming_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎲 Suggest Random Movie",
                    callback_data="random_movie"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 WATCHLIST",
                    callback_data="watchlist_open"
                )
            ]
        ]
    )
