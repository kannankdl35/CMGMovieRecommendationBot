# Location: keyboards/home.py  (REPLACE ENTIRE FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_home_text(first_name=None):
    """Text shown on the Home/Welcome menu - shared by plugins/start.py's
    /start command and plugins/callback.py's "back_home" /
    "home_from_search" callbacks, so the wording only has to change in
    one place. `first_name` is the Telegram user's first name (falls
    back to "there" if unavailable)."""
    name = first_name or "there"
    return (
        f"👋 Hey {name},\n\n"
        "__Discover movies, shows, ratings, trending titles, and more — "
        "all in one place.__ 🎬\n\n"
        "Choose an option below to begin ⬇️."
    )


def home_keyboard():
    """The Home menu buttons, top to bottom:

      1. 🔍 SEARCH - TMDb
      2. 🔍 SEARCH - IMDb
      3. ⬇️ DOWNLOAD POSTERS
      4. 📈 TRENDING        | 📨 UPCOMING   (same row)
      5. 🎲 RANDOM          | 🗒️ WATCHLIST  (same row)
      6. ⚙️ SETTINGS        | ℹ️ ABOUT       (same row)
      7. 📅 THIS MONTH WATCHED

    All three of the first buttons use Telegram Inline Mode, same as the
    old "Find Movies & Series" button - switch_inline_query_current_chat
    pre-fills "@<BotUsername> imdb " / "@<BotUsername> tmdb " /
    "@<BotUsername> posters " into this chat's message box. The leading
    "imdb "/"tmdb "/"posters " word is how plugins/inline.py's single
    inline-query handler tells which backend to search and what to do once
    a result is picked (services.imdb vs services.tmdb, and full details
    page vs posters-only) - Telegram doesn't otherwise report which button
    was tapped, only the text the user ends up typing.

    ✅ "⬇️ DOWNLOAD POSTERS" (switch_inline_query_current_chat="posters ")
    reuses the exact same inline search workflow as "🔍 SEARCH - TMDb"
    (type a title, tap a result) but skips the details page entirely -
    picking a result fetches every poster TMDb has on file for that title
    (services/tmdb.py's fetch_posters_tmdb()) and sends them as plain
    images, with no caption, no buttons, and no other title info. See
    plugins/inline.py and plugins/posters.py.

    "📈 TRENDING" (callback_data="trending_open") opens the
    Today / This Week / Home selection page (keyboards/trending.py),
    powered by TMDb's trending endpoints.

    "📨 UPCOMING" (callback_data="upcoming_open") opens a
    Theatre Release / OTT Release This Week / Back selection page
    (keyboards/upcoming.py), each leading to a language picker
    (Malayalam/Tamil/Telugu/Kannada/Hindi/English) and then a numbered
    release list - see services/theatre_releases.py,
    services/ott_releases.py, and plugins/callback.py.

    ✅ "🎲 RANDOM" (callback_data="random_open") opens a
    Language selection page (keyboards/random_movies.py: Malayalam, Tamil,
    Hindi, Kannada, Telugu, English, Korean, Others). Picking a language
    fetches a batch of random TMDb movies in that language (Others =
    anything outside the other seven) meeting that language's rating/vote
    floor, and shows them as a numbered list - tapping a number opens the
    full details page. All handled in plugins/callback.py, backed by
    services/tmdb.py's get_random_movies_by_language() /
    get_random_movies_other_languages().

    ✅ "📅 THIS MONTH WATCHED" (callback_data="month_watched_open") opens
    the current calendar month's watched list (movies + series the user
    tapped "➕ Add to This Month Watched" on), that month's stats, and a
    "🏆 See the Achievements" page - see keyboards/month_watched.py,
    database/month_watched_db.py, and plugins/month_watched.py.

    ✅ "⚙️ SETTINGS" (callback_data="settings_open") opens the
    IMDb Settings / TMDb Settings selection page (keyboards/settings.py),
    where each user can toggle which detail fields (Poster, Title, Year,
    Rating, Plot, ...) appear in their IMDb/TMDb movie/series details -
    see database/settings_db.py and plugins/callback.py.

    ✅ "ℹ️ ABOUT" (callback_data="about_open") opens the About page
    (Bot Name, Description, Version, Developer/Admin, Channel, etc.) with
    a "🐞 Report Issues/Bugs" button underneath - all the shown text lives
    in about/about_info.py so it's editable on its own, see
    keyboards/about.py and plugins/callback.py.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔍 SEARCH - TMDb",
                    switch_inline_query_current_chat="tmdb "
                )
            ],
            [
                InlineKeyboardButton(
                    "🔍 SEARCH - IMDb",
                    switch_inline_query_current_chat="imdb "
                )
            ],
            [
                InlineKeyboardButton(
                    "⬇️ DOWNLOAD POSTERS",
                    switch_inline_query_current_chat="posters "
                )
            ],
            [
                InlineKeyboardButton(
                    "📈 TRENDING",
                    callback_data="trending_open"
                ),
                InlineKeyboardButton(
                    "📨 UPCOMING",
                    callback_data="upcoming_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎲 RANDOM",
                    callback_data="random_open"
                ),
                InlineKeyboardButton(
                    "🗒️ WATCHLIST",
                    callback_data="watchlist_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ SETTINGS",
                    callback_data="settings_open"
                ),
                InlineKeyboardButton(
                    "ℹ️ ABOUT",
                    callback_data="about_open"
                )
            ],
            [
                InlineKeyboardButton(
                    "📅 THIS MONTH WATCHED",
                    callback_data="month_watched_open"
                )
            ]
        ]
    )
