import asyncio

from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.home import home_keyboard

# 🔥 Trending Now keyboards (Today/This Week/Home selection page + the
# numbered listing keyboard), and the TMDb trending fetcher.
from keyboards.trending import trending_menu_keyboard, trending_list_keyboard
from services.tmdb import get_trending_tmdb

# Per-user in-memory storage of the last trending listing fetched, so the
# numbered buttons under it can be mapped back to a title (see
# database/user_state.py).
from database.user_state import save_trending_results, get_trending_results

# 🎬 Upcoming Movies (Theatre Release / OTT Release This Week) keyboards +
# data sources - see keyboards/upcoming.py, services/theatre_releases.py,
# services/ott_releases.py.
from keyboards.upcoming import upcoming_category_keyboard, upcoming_language_keyboard, upcoming_list_keyboard
from services.theatre_releases import get_cached_theatre_releases
from services.ott_releases import get_cached_ott_releases, resolve_release_key

# Watchlist database helpers
from database.watchlist_db import add_to_watchlist, remove_from_watchlist

# Shared watchlist text/keyboard builder + the delete-then-resend helper,
# used by the Watchlist Home button (callback_data="watchlist_open" below)
# and by the /watchlist command in plugins/watchlist.py. Everything renders
# inside this Telegram chat - no Web App / external page.
from plugins.watchlist import send_watchlist_view

from plugins.details import (
    send_imdb_details,        # details renderer (search results / watchlist)
    send_trending_details,     # details renderer for 🔥 Trending Now / 🎬 Upcoming Movies (adds OTT status)
    fetch_details,             # resolves an IMDb id or a TMDb key to details
    build_details_keyboard,    # shared Watchlist/Search Another/Done keyboard builder
)


HOME_TEXT = (
    "👋 **Welcome to CMG Movie Recommendation Bot**\n\n"
    "🎬 Find any Movie or TV Series and see its full details -\n"
    "poster, rating, cast, and plot.\n\n"
    "• 🔍 **SEARCH - IMDb** - search powered by IMDb\n"
    "• 🔍 **SEARCH - TMDb** - search powered by TMDb\n"
    "• 🔥 **TRENDING NOW** - what's trending today/this week on TMDb\n"
    "• 🎬 **UPCOMING MOVIES** - theatre & OTT releases by language\n"
    "• 📋 **WATCHLIST** - your saved titles\n\n"
    "Click a button below to get started."
)

TRENDING_MENU_TEXT = (
    "🔥 **Trending Now**\n\n"
    "See what's trending on TMDb right now.\n\n"
    "• 📅 **Today** - trending today\n"
    "• 📈 **This Week** - trending this week\n\n"
    "Pick one below 👇"
)

UPCOMING_CATEGORY_TEXT = (
    "🎬 **Upcoming Movies**\n\n"
    "• 🎬 **Theatre Release** - upcoming theatrical releases\n"
    "• 📺 **OTT Release This Week** - recent/upcoming OTT releases\n\n"
    "Pick one below 👇"
)

CATEGORY_LABELS = {
    "theatre": "🎬 Theatre Release",
    "ott": "📺 OTT Release This Week",
}


def _upcoming_language_text(category):
    return f"{CATEGORY_LABELS.get(category, category.title())}\n\nPick a language below 👇"


@Client.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):

    data = callback.data
    user_id = callback.from_user.id

    # ---------------- HOME ----------------

    if data == "back_home":

        await callback.message.edit_text(
            text=HOME_TEXT,
            reply_markup=home_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: MENU ----------------
    # Fired from the main menu's "🔥 Trending Now" button
    # (callback_data="trending_open", see keyboards/home.py). Shows the
    # Today / This Week / Home selection page (keyboards/trending.py),
    # edited in place over the main menu message.

    if data == "trending_open":

        await callback.message.edit_text(
            text=TRENDING_MENU_TEXT,
            reply_markup=trending_menu_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: TODAY / THIS WEEK ----------------
    # Fetches TMDb's daily/weekly trending titles, stores them for this
    # user (so the numbered buttons below can be mapped back to a title -
    # database/user_state.py), and shows them as a numbered list with
    # numbered buttons underneath (keyboards/trending.py's
    # trending_list_keyboard()), 5 per row.

    if data in ("trending_day", "trending_week"):

        period = "day" if data == "trending_day" else "week"
        period_label = "Today" if period == "day" else "This Week"

        results = await asyncio.to_thread(get_trending_tmdb, period)

        # API failure (network error, bad key, non-2xx) - get_trending_tmdb()
        # returns None in that case, distinct from a successful-but-empty list.
        if results is None:
            await callback.answer(
                "⚠️ Couldn't fetch trending titles right now. Please try again.",
                show_alert=True,
            )
            return

        save_trending_results(user_id, results)

        if not results:
            await callback.message.edit_text(
                text=f"😕 No trending titles found for **{period_label}** right now.",
                reply_markup=trending_menu_keyboard()
            )
            await callback.answer()
            return

        lines = [f"🔥 **Trending - {period_label}**\n"]

        for index, item in enumerate(results, start=1):
            icon = "📺" if item.get("Type") == "series" else "🎬"
            lines.append(f"{index}. {icon} {item.get('Title')} ({item.get('Year')})")

        lines.append("\nTap a number below to see full details 👇")

        await callback.message.edit_text(
            text="\n".join(lines),
            reply_markup=trending_list_keyboard(len(results))
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: BACK ----------------
    # Fired from "⬅ Back" under a trending listing - returns to the
    # Today / This Week / Home selection page (NOT the main menu).

    if data == "trend_back":

        await callback.message.edit_text(
            text=TRENDING_MENU_TEXT,
            reply_markup=trending_menu_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🔥 TRENDING NOW: ITEM SELECTED ----------------
    # Fired when the user taps one of the numbered buttons under a
    # trending listing ("trend_sel_<n>"). Looks up item `n` in the
    # trending results this user last fetched, and sends its full details
    # page (poster + info + OTT Release Status) as a NEW message - the
    # trending listing itself is left in place so "⬅ Back" still works.

    if data.startswith("trend_sel_"):

        try:
            index = int(data.replace("trend_sel_", "", 1))
        except ValueError:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        results = get_trending_results(user_id)

        if not results or index < 1 or index > len(results):
            await callback.answer(
                "This trending list has expired. Please reopen 🔥 Trending Now.",
                show_alert=True,
            )
            return

        key_id = results[index - 1].get("imdbID")

        await send_trending_details(
            client, callback.message.chat.id, key_id, user_id=user_id
        )

        await callback.answer()
        return

    # ---------------- 🎬 UPCOMING MOVIES: CATEGORY MENU ----------------
    # Fired from the main menu's "🎬 Upcoming Movies" button
    # (callback_data="upcoming_open", see keyboards/home.py). Shows the
    # Theatre Release / OTT Release This Week / Back selection page
    # (keyboards/upcoming.py), edited in place over the main menu message.

    if data == "upcoming_open":

        await callback.message.edit_text(
            text=UPCOMING_CATEGORY_TEXT,
            reply_markup=upcoming_category_keyboard()
        )

        await callback.answer()
        return

    # ---------------- 🎬 UPCOMING MOVIES: CATEGORY SELECTED / BACK-TO-LANGUAGE-MENU ----------------
    # Fired both when a category is first tapped ("upcoming_cat_theatre" /
    # "upcoming_cat_ott") AND when "🔙 Back" is tapped under a release
    # listing (keyboards/upcoming.py's upcoming_list_keyboard() reuses the
    # same callback_data) - both cases show the same language picker.

    if data.startswith("upcoming_cat_"):

        category = data.replace("upcoming_cat_", "", 1)

        if category not in CATEGORY_LABELS:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        await callback.message.edit_text(
            text=_upcoming_language_text(category),
            reply_markup=upcoming_language_keyboard(category)
        )

        await callback.answer()
        return

    # ---------------- 🎬 UPCOMING MOVIES: LANGUAGE SELECTED ----------------
    # Fetches the release list for this category+language (Theatre ->
    # services.theatre_releases, OTT -> services.ott_releases - both
    # cached, refreshed at most once a day) and shows it as a numbered
    # list with numbered buttons underneath
    # (keyboards/upcoming.py's upcoming_list_keyboard()).

    if data.startswith("upcoming_lang_"):

        remainder = data[len("upcoming_lang_"):]

        try:
            category, lang = remainder.split("_", 1)
        except ValueError:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        if category == "theatre":
            entries = await asyncio.to_thread(get_cached_theatre_releases, lang)
        elif category == "ott":
            releases = await asyncio.to_thread(get_cached_ott_releases)
            entries = releases.get(lang, [])
        else:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        entries = entries[:15]

        if not entries:
            await callback.message.edit_text(
                text=(
                    f"{CATEGORY_LABELS.get(category, category.title())} - "
                    f"**{lang.title()}**\n\n"
                    "😕 No releases found right now."
                ),
                reply_markup=upcoming_language_keyboard(category)
            )
            await callback.answer()
            return

        lines = [f"{CATEGORY_LABELS.get(category, category.title())} - **{lang.title()}**\n"]

        for index, entry in enumerate(entries, start=1):
            release_date = entry.get("release_date")
            platform = entry.get("platform")
            suffix_parts = [p for p in (release_date, platform) if p]
            suffix = f" — {' · '.join(suffix_parts)}" if suffix_parts else ""
            lines.append(f"{index}. {entry.get('title')}{suffix}")

        lines.append("\nTap a number below to see full details 👇")

        await callback.message.edit_text(
            text="\n".join(lines),
            reply_markup=upcoming_list_keyboard(category, lang, len(entries))
        )

        await callback.answer()
        return

    # ---------------- 🎬 UPCOMING MOVIES: ITEM SELECTED ----------------
    # Fired when the user taps one of the numbered buttons under a release
    # listing ("upcoming_sel_<category>_<lang>_<n>"). Theatre Release
    # entries already carry a real TMDb key_id (services.theatre_releases
    # builds it directly from TMDb's own discover results), so those go
    # straight to the rich details page. OTT Release entries from the
    # scraped regional languages don't have one yet - resolve_release_key()
    # tries to find a TMDb match lazily, only for this tapped item; if it
    # can't find a confident match, this falls back to a plain info card
    # built from the scraped fields (same fallback used previously for the
    # standalone OTT Releases feature).

    if data.startswith("upcoming_sel_"):

        remainder = data[len("upcoming_sel_"):]

        try:
            category, lang, index_str = remainder.split("_", 2)
            index = int(index_str)
        except ValueError:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        if category == "theatre":
            entries = await asyncio.to_thread(get_cached_theatre_releases, lang)
        elif category == "ott":
            releases = await asyncio.to_thread(get_cached_ott_releases)
            entries = releases.get(lang, [])
        else:
            await callback.answer("Something went wrong. Please try again.", show_alert=True)
            return

        if not entries or index < 1 or index > len(entries):
            await callback.answer(
                "This list may have refreshed. Please reopen 🎬 Upcoming Movies.",
                show_alert=True,
            )
            return

        entry = entries[index - 1]
        key_id = entry.get("key_id")

        if not key_id and category == "ott":
            key_id = await asyncio.to_thread(resolve_release_key, entry)

        if key_id:
            await send_trending_details(
                client, callback.message.chat.id, key_id, user_id=user_id
            )
        else:
            # No confident TMDb match - show what was scraped directly.
            # No Watchlist button here since there's no stable id to
            # attach it to.
            text_lines = [f"🎬 **{entry.get('title')}**\n"]
            if entry.get("release_date"):
                text_lines.append(f"📅 Release Date: {entry.get('release_date')}")
            if entry.get("platform"):
                text_lines.append(f"📡 Platform: {entry.get('platform')}")
            if entry.get("genre"):
                text_lines.append(f"🎭 Genre: {entry.get('genre')}")
            text_lines.append(f"🗣 Language: {entry.get('language') or lang.title()}")

            await callback.message.reply_text(
                "\n".join(text_lines),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("✅ Done", callback_data="done")]]
                )
            )

        await callback.answer()
        return

    # ---------------- SEARCH (SEARCH - IMDb / SEARCH - TMDb) ----------------
    # Both search buttons are handled entirely by Telegram Inline Mode (see
    # keyboards/home.py + plugins/inline.py). The buttons don't send
    # callback_data, so there's nothing to handle here.

    # ---------------- SEARCH RESULT SELECTED ----------------
    # Fired when the user taps "View Details" on a card sent from an inline
    # search result (plugins/inline.py). `imdb_id` here is either a real
    # IMDb id (SEARCH - IMDb) or a TMDb key like "tmdb_movie_603"
    # (SEARCH - TMDb) - fetch_details()/send_imdb_details() in
    # plugins/details.py both already know how to tell those apart.

    if data.startswith("sr_"):

        imdb_id = data.replace("sr_", "", 1)

        chat_id = callback.message.chat.id if callback.message else callback.from_user.id

        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_text(
                    inline_message_id=callback.inline_message_id,
                    text="✅ Details opened below.",
                )
            except Exception:
                try:
                    await client.edit_inline_caption(
                        inline_message_id=callback.inline_message_id,
                        caption="✅ Details opened below.",
                    )
                except Exception:
                    pass

        await send_imdb_details(client, chat_id, imdb_id, user_id=user_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST ----------------

    if data == "watchlist_open":

        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_watchlist_view(client, callback.message.chat.id, user_id)

        await callback.answer()
        return

    # ---------------- WATCHLIST: ITEM SELECTED ----------------

    if data.startswith("wl_"):

        imdb_id = data.replace("wl_", "", 1)

        await send_imdb_details(
            client, callback.message.chat.id, imdb_id,
            user_id=user_id, in_watchlist=True, context="watchlist",
        )

        await callback.answer()
        return

    # ---------------- ADD TO WATCHLIST ----------------

    if data.startswith("addwl_"):

        imdb_id = data.replace("addwl_", "", 1)

        details = await asyncio.to_thread(fetch_details, imdb_id)

        if not details:
            await callback.answer("Could not add this title. Please try again.", show_alert=True)
            return

        poster = details.get("Poster")
        poster = poster if poster and poster != "N/A" else None

        added = await add_to_watchlist(
            user_id=user_id,
            imdb_id=imdb_id,
            title=details.get("Title"),
            poster=poster,
            year=details.get("Year"),
            media_type=details.get("Type", "movie"),
        )

        new_markup = build_details_keyboard(imdb_id, in_watchlist=True, context="search")

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=new_markup)
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_reply_markup(
                    callback.inline_message_id, reply_markup=new_markup
                )
            except Exception:
                pass

        if added:
            await callback.answer("Added to Watchlist ✅")
        else:
            await callback.answer("Already in your Watchlist.")

        return

    # ---------------- REMOVE FROM WATCHLIST, IN PLACE ----------------

    if data.startswith("rmwl_"):

        imdb_id = data.replace("rmwl_", "", 1)

        await remove_from_watchlist(user_id, imdb_id)

        new_markup = build_details_keyboard(imdb_id, in_watchlist=False, context="search")

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=new_markup)
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_reply_markup(
                    callback.inline_message_id, reply_markup=new_markup
                )
            except Exception:
                pass

        await callback.answer("Removed from Watchlist 🗑", show_alert=True)
        return

    # ---------------- DONE ----------------

    if data == "done":

        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        elif callback.inline_message_id:
            try:
                await client.edit_inline_caption(
                    callback.inline_message_id, "✅ Done.", reply_markup=None
                )
            except Exception:
                try:
                    await client.edit_inline_text(
                        callback.inline_message_id, "✅ Done.", reply_markup=None
                    )
                except Exception:
                    pass

        await callback.answer()
        return

    # ---------------- DELETE FROM WATCHLIST ----------------

    if data.startswith("delwl_"):

        imdb_id = data.replace("delwl_", "", 1)

        await remove_from_watchlist(user_id, imdb_id)

        chat_id = callback.message.chat.id

        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_watchlist_view(client, chat_id, user_id)

        await callback.answer("Removed from Watchlist 🗑")
        return

    # ---------------- UNKNOWN ----------------

    await callback.answer()
