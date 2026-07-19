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


def _clean(value):
    """The IMDb API leaves unavailable fields as None - treat that the
    same as missing so it's skipped instead of printed."""
    if not value or value == "N/A":
        return None
    return value


def _build_card_caption(label, title, year, extra):
    """Build the inline search-result card caption.

    CHANGED: Previously this was just the media type + title + year
    (e.g. "Movie\n**Iron Man 3** (2013)"). Now also shows Language and
    Release Date when the IMDb API has them, so the first message a user sees
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
    """Best-effort lookup of Type + Release Date + Language for one search
    result.

    Unlike OMDb's old search endpoint, the IMDb API's /search?q= results
    don't report a movie/series type, a full release date, or a language
    up front - all three require a separate per-title lookup. Failures
    here just mean the type falls back to "movie" and the two extra
    caption lines are omitted; they never block showing the result.
    """
    details = get_details(imdb_id)
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

    Replaces the old flow where the bot asked the user to type the title
    directly into the chat after pressing a button. Selecting a result here
    inserts this short card into the chat, still carrying an "ℹ️ View
    Details" button ('sr_<imdbID>' callback_data, handled in
    plugins/callback.py) as a fallback.

    ✅ CHANGED (Feature 6): normally the user never needs that button at
    all - the instant Telegram reports the result as chosen,
    inline_result_chosen() below edits this same card in place into the
    full details page (poster + full info + Trailer/Watchlist/Done), so
    the full details show up automatically right after selecting the
    movie/series from the inline results. The "View Details" button only
    still matters as a fallback for the rare case Telegram inline
    feedback isn't enabled for this bot (via @BotFather's
    /setinlinefeedback) and the chosen-result edit never fires.
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
        poster = item.get("Poster")

        if not imdb_id:
            continue

        # NEW: pull Type + Language + Release Date for this title so the
        # very first card the user sees isn't just the bare title
        # (Feature 4 fix). The IMDb search endpoint doesn't report a
        # movie/series type up front the way OMDb's did, so this lookup
        # now also decides the 📺/🎬 label - defaults to "movie" if it
        # can't be determined.
        extra = _fetch_extra_info(imdb_id)
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
