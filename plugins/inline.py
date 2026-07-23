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

from services.imdb import search_titles
from services.tmdb import search_titles_tmdb

from plugins.details import send_imdb_details_inline

# Telegram allows up to 50 inline results per answer; capped lower to keep
# results relevant and responses fast.
INLINE_RESULT_LIMIT = 20


def _parse_mode(raw_query):
    """The Home menu's two search buttons (keyboards/home.py) pre-fill
    '@<BotUsername> imdb ' / '@<BotUsername> tmdb ' into the chat's inline
    query box - this is the only signal this single handler gets about
    which button was tapped, since Telegram's inline query event carries
    just the text the user typed, not which button produced it.
    Typing '@<BotUsername> <text>' directly, with no recognized prefix,
    defaults to IMDb.
    """
    text = raw_query.strip()
    lowered = text.lower()

    if lowered.startswith("tmdb"):
        return "tmdb", text[4:].strip()
    if lowered.startswith("imdb"):
        return "imdb", text[4:].strip()

    return "imdb", text


def _build_card_caption(label, title, year, mode):
    source = "IMDb" if mode == "imdb" else "TMDb"
    return f"{label}\n**{title}** ({year})\n🔎 Source : {source}"


@Client.on_inline_query()
async def inline_search_handler(client: Client, inline_query: InlineQuery):
    """Handle inline search for both 'SEARCH - IMDb' and 'SEARCH - TMDb'
    (see keyboards/home.py). Selecting a result inserts a short card into
    the chat, which then edits itself in place into the full details page
    the instant Telegram reports it as chosen (inline_result_chosen()
    below) - the 'ℹ️ View Details' button is a fallback for when inline
    feedback isn't enabled for the bot.
    """
    mode, query = _parse_mode(inline_query.query)

    if not query:
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
            switch_pm_text=f"Type a title to search ({mode.upper()}) 🔎",
            switch_pm_parameter="start",
        )
        return

    search_fn = search_titles_tmdb if mode == "tmdb" else search_titles

    # Blocking HTTP request - run off the event loop so the bot can keep
    # handling other updates while it's in flight.
    results_data = await asyncio.to_thread(search_fn, query)

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

    answers = []

    for item in results_data:
        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        # For IMDb mode this is a real "tt..." id. For TMDb mode this is a
        # composite key like "tmdb_movie_603" (see services/tmdb.py) - both
        # flow untouched through callback_data / chosen-result handling;
        # plugins/details.py's fetch_details() is what tells them apart.
        item_id = item.get("imdbID")
        poster = item.get("Poster")
        media_type = item.get("Type", "movie")

        if not item_id:
            continue

        label = "📺 Series" if media_type == "series" else "🎬 Movie"
        description = f"{label} • {year} • {mode.upper()}"
        caption = _build_card_caption(label, title, year, mode)

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("ℹ️ View Details", callback_data=f"sr_{item_id}")]]
        )

        if poster and poster != "N/A":
            answers.append(
                InlineQueryResultPhoto(
                    id=item_id,
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
                    id=item_id,
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


@Client.on_chosen_inline_result()
async def inline_result_chosen(client: Client, chosen: ChosenInlineResult):
    """Fires the instant a user taps one of the inline results above. Turns
    that short "via @BotName" card straight into the full details page
    (poster + full info + Trailer/Watchlist/Done buttons) by editing it in
    place - no separate "View Details" tap required.

    IMPORTANT: this requires inline feedback to be enabled for the bot -
    in @BotFather run /setinlinefeedback, pick this bot, and set it to
    100%. Without that, Telegram will not reliably report chosen results
    and this handler won't fire (the "ℹ️ View Details" button on the card
    stays as the fallback in that case).
    """
    # The result id was set to the title's item_id (IMDb id or TMDb key)
    # when the card was built above.
    item_id = chosen.result_id

    # inline_message_id is only present when the bot can edit the message
    # it just caused Telegram to insert (requires inline feedback to be
    # enabled, see note above). Nothing to edit otherwise.
    if not item_id or not chosen.inline_message_id:
        return

    user_id = chosen.from_user.id if chosen.from_user else None

    await send_imdb_details_inline(
        client, chosen.inline_message_id, item_id, user_id=user_id
    )
