# Location: keyboards/home.py  (REPLACE ENTIRE FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def home_keyboard():
    """The Home menu has seven buttons:

      1. 🔍 SEARCH - IMDb
      2. 🔍 SEARCH - TMDb
      3. 🔥 TRENDING NOW
      4. 🎬 UPCOMING MOVIES
      5. 🎲 SUGGEST RANDOM MOVIE
      6. 📋 WATCHLIST
      7. 🗓️ THIS MONTH WATCHED

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

    ✅ "🎲 Suggest Random Movie" (callback_data="random_open") opens a
    Language selection page (keyboards/random_movies.py: Malayalam, Tamil,
    Hindi, Kannada, Telugu, English, Korean, Others). Picking a language
    fetches a batch of random TMDb movies in that language (Others =
    anything outside the other seven) meeting that language's rating/vote
    floor, and shows them as a numbered list - tapping a number opens the
    full details page. All handled in plugins/callback.py, backed by
    services/tmdb.py's get_random_movies_by_language() /
    get_random_movies_other_languages().

    ✅ "🗓️ This Month Watched" (callback_data="month_watched_open") opens
    the current calendar month's watched list (movies + series the user
    tapped "➕ Add to This Month Watched" on), that month's stats, and a
    "🏆 See the Achievements" page - see keyboards/month_watched.py,
    database/month_watched_db.py, and plugins/month_watched.py.
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
                    callback_data="random_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 WATCHLIST",
                    callback_data="watchlist_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗓️ This Month Watched",
                    callback_data="month_watched_open"
                )
            ]
        ]
    )
