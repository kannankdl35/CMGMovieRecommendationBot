import asyncio

from pyrogram import Client
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChosenInlineResult,
)

from services.imdb import search_titles, get_details

# ✅ NEW (Feature 6): renders the full details page directly onto an
# inline-inserted card the moment it's chosen - see
# inline_result_chosen() at the bottom of this file.
from plugins.details import send_imdb_details_inline

# Feature 1 - Find Movies & Series (now via Telegram Inline Mode)
# Telegram allows up to 50 inline results per answer; we cap it lower
# to keep results relevant and responses fast.
INLINE_RESULT_LIMIT = 20

# ---------------------------------------------------------------------------
# ✅ BUGFIX: the inline query list was previously coming back empty
# ("QUERY_ID_INVALID" in the logs). The handler was fetching Type +
# Language + Release Date for EACH search result ONE AT A TIME
# (`get_details()`, which used to make up to 3 blocking HTTP calls per
# title) before ever calling `inline_query.answer()`. With up to
# INLINE_RESULT_LIMIT results that could take well over Telegram's inline
# query timeout, so by the time the bot tried to answer, Telegram had
# already invalidated the query id and the answer was silently dropped -
# no results ever showed up in the inline list.
#
# Fixed by:
#   1. get_details() itself now makes a single HTTP request instead of up
#      to 3 (services/imdb.py no longer calls out to TMDB at all).
#   2. All per-result lookups below now run CONCURRENTLY (via
#      asyncio.to_thread, since `requests` is blocking) instead of one at
#      a time, each capped at PER_ITEM_TIMEOUT seconds - a single slow/
#      hanging title can no longer stall the whole list. Whatever doesn't
#      finish in time is simply skipped and that card falls back to
#      defaults (🎬 Movie label, no extra caption lines) rather than
#      blocking the response.
# ---------------------------------------------------------------------------

PER_ITEM_TIMEOUT = 4  # seconds - per-title enrichment lookup budget


def _clean(value):
    """The IMDb API leaves unavailable fields as None - treat that the
    same as missing so it's skipped instead of printed."""
    if not value or value == "N/A":
        return None
    return value


def _build_card_caption(label, title, year, extra):
    """Build the inline search-result card caption.

    Shows Language and Release Date when the IMDb API has them, so the
    first message a user sees already carries more than just the name
    (Feature 4 fix).
    """
    caption = f"{label}\n**{title}** ({year})"

    release_date = extra.get("release_date")
    language = extra.get("language")

    if release_date:
        caption += f"\n📅 Release : {release_date}"
    if language:
        caption += f"\n🗣 Language : {language}"

    return caption


async def _fetch_extra_info(imdb_id):
    """Best-effort lookup of Type + Release Date + Language for one search
    result, run off the event loop (get_details() does a blocking HTTP
    request) and capped at PER_ITEM_TIMEOUT seconds.

    Failures/timeouts here just mean the type falls back to "movie" and
    the two extra caption lines are omitted for that one card; they never
    block or delay the rest of the results.
    """
    try:
        details = await asyncio.wait_for(
            asyncio.to_thread(get_details, imdb_id), timeout=PER_ITEM_TIMEOUT
        )
    except Exception:
        return {}

    if not details:
        return {}

    return {
        "type": details.get("Type"),
        "release_date": _clean(details.get("Year")),
        "language": _clean(details.get("Language")),
    }


@Client.on_inline_query()
async def inline_search_handler(client: Client, inline_query: InlineQuery):
    """Handle inline search: user types '@<BotUsername> <title>' in any chat
    (or taps 🔍 Find Movies & Series, which pre-fills this in the current chat).

    Selecting a result here inserts a short card into the chat, which then
    edits itself in place into the full details page the instant Telegram
    reports it as chosen (inline_result_chosen() below) - see Feature 6
    notes there. The "ℹ️ View Details" button is a fallback for when
    inline feedback isn't enabled for the bot.
    """
    query = inline_query.query.strip()

    if not query:
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
            switch_pm_text="Type a movie or series name to search 🔎",
            switch_pm_parameter="start",
        )
        return

    # search_titles() does a blocking HTTP request - run it off the event
    # loop so the bot can keep handling other updates while it's in flight.
    results_data = await asyncio.to_thread(search_titles, query)

    if not results_data:
        await inline_query.answer(
            results=[],
            cache_time=5,
            is_personal=True,
            switch_pm_text=f"No results found for '{query}'",
            switch_pm_parameter="start",
        )
        return

    results_data = results_data[:INLINE_RESULT_LIMIT]

    # Fetch the Type/Language/Release-date enrichment for every result IN
    # PARALLEL (see module note above) instead of one at a time.
    extras = await asyncio.gather(
        *[_fetch_extra_info(item.get("imdbID")) for item in results_data]
    )

    answers = []

    for item, extra in zip(results_data, extras):
        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        imdb_id = item.get("imdbID")
        poster = item.get("Poster")

        if not imdb_id:
            continue

        media_type = extra.get("type") or "movie"

        label = "📺 Series" if media_type == "series" else "🎬 Movie"
        description = f"{label} • {year}"

        caption = _build_card_caption(label, title, year, extra)

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("ℹ️ View Details", callback_data=f"sr_{imdb_id}")]]
        )

        if poster and poster != "N/A":
            answers.append(
                InlineQueryResultPhoto(
                    id=imdb_id,
                    photo_url=poster,
                    thumb_url=poster,
                    title=title,
                    description=description,
                    caption=caption,
                    reply_markup=buttons,
                )
            )
        else:
            # Fall back to a text-only card when there's no poster
            answers.append(
                InlineQueryResultArticle(
                    id=imdb_id,
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(caption),
                    reply_markup=buttons,
                )
            )

    await inline_query.answer(
        results=answers,
        cache_time=30,
        is_personal=True,
    )


# ---------------------------------------------------------------------------
# ✅ NEW (Feature 6): fires the instant a user taps one of the inline
# results above. Turns that short "via @BotName" card straight into the
# full details page (poster + full info + Trailer/Watchlist/Done buttons)
# by editing it in place - no separate "View Details" tap required.
#
# IMPORTANT: this requires inline feedback to be enabled for the bot -
# in @BotFather run /setinlinefeedback, pick this bot, and set it to
# 100%. Without that, Telegram will not reliably report chosen results
# and this handler won't fire (the "ℹ️ View Details" button on the card
# stays as the fallback in that case).
# ---------------------------------------------------------------------------

@Client.on_chosen_inline_result()
async def inline_result_chosen(client: Client, chosen: ChosenInlineResult):
    # The result id was set to the title's imdbID when the card was built
    # above (id=imdb_id on both InlineQueryResultPhoto and
    # InlineQueryResultArticle).
    imdb_id = chosen.result_id

    # inline_message_id is only present when the bot can edit the message
    # it just caused Telegram to insert (requires inline feedback to be
    # enabled, see note above, and reply_markup to have been attached to
    # the chosen result - both true here). Nothing to edit otherwise.
    if not imdb_id or not chosen.inline_message_id:
        return

    user_id = chosen.from_user.id if chosen.from_user else None

    await send_imdb_details_inline(
        client, chosen.inline_message_id, imdb_id, user_id=user_id
    )
