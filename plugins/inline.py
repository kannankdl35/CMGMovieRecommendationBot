from pyrogram import Client
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from services.omdb import search_titles, get_details

# Feature 1 - Find Movies & Series (now via Telegram Inline Mode)
# Telegram allows up to 50 inline results per answer; we cap it lower
# to keep results relevant and responses fast.
INLINE_RESULT_LIMIT = 20


def _clean(value):
    """OMDb uses the literal string 'N/A' for missing fields - treat that
    the same as missing so it's skipped instead of printed as 'N/A'."""
    if not value or value == "N/A":
        return None
    return value


def _build_card_caption(label, title, year, extra):
    """Build the inline search-result card caption.

    CHANGED: Previously this was just the media type + title + year
    (e.g. "Movie\n**Iron Man 3** (2013)"). Now also shows Language and
    Release Date when OMDb has them, so the first message a user sees
    already carries more than just the name (Feature 4 fix).
    """
    caption = f"{label}\n**{title}** ({year})"

    release_date = extra.get("release_date")
    language = extra.get("language")

    if release_date:
        caption += f"\n📅 Release : {release_date}"
    if language:
        caption += f"\n🗣 Language : {language}"

    return caption


def _fetch_extra_info(imdb_id):
    """Best-effort lookup of Release Date + Language for one search result.

    OMDb's search endpoint (used by search_titles) only returns
    Title/Year/imdbID/Type/Poster - Language and full Release date require
    a separate per-title lookup. Failures here just mean those two extra
    lines are omitted from the card; they never block showing the result.
    """
    details = get_details(imdb_id)
    if not details:
        return {}

    return {
        "release_date": _clean(details.get("Released")),
        "language": _clean(details.get("Language")),
    }


@Client.on_inline_query()
async def inline_search_handler(client: Client, inline_query: InlineQuery):
    """Handle inline search: user types '@<BotUsername> <title>' in any chat
    (or taps 🔍 Find Movies & Series, which pre-fills this in the current chat).

    Replaces the old flow where the bot asked the user to type the title
    directly into the chat after pressing a button. Selecting a result here
    sends a card into the chat with an "ℹ️ View Details" button using the
    same 'sr_<imdbID>' callback_data already handled in plugins/callback.py,
    so Feature 2/3/5 (details, trailer, watchlist) keep working unchanged.
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

    results_data = search_titles(query)

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
        imdb_id = item.get("imdbID")
        media_type = item.get("Type", "movie")
        poster = item.get("Poster")

        if not imdb_id:
            continue

        label = "📺 Series" if media_type == "series" else "🎬 Movie"
        description = f"{label} • {year}"

        # NEW: pull Language + Release Date for this title so the very
        # first card the user sees isn't just the bare title (Feature 4 fix).
        extra = _fetch_extra_info(imdb_id)
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
