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

# ✅ NEW - /stats command: bumps the all-time "Total Searches" counter
# once per real, settled search (see the call site below and
# database/stats_db.py).
from database.stats_db import increment_search_count

# Telegram allows up to 50 inline results per answer; capped lower to keep
# results relevant and responses fast.
INLINE_RESULT_LIMIT = 20

# ⬇️ DOWNLOAD POSTERS (keyboards/home.py) reuses this same inline-query
# handler and the same TMDb search backend as SEARCH - TMDb, but tags its
# result ids/callback_data with this prefix so inline_result_chosen() below
# and plugins/callback.py's "dp_" branch both know to fetch-and-send posters
# instead of opening the normal details page - the underlying TMDb key
# ("tmdb_movie_603" / "tmdb_tv_1396") is otherwise identical either way.
POSTERS_ID_PREFIX = "dp_"

# ---------------------------------------------------------------------------
# STALE-ANSWER GUARD + DEBOUNCE
#
# Telegram fires a fresh inline query on every keystroke (typing "Kuruvi"
# can send separate query events for "K", "Ku", "Kur", ... "Kuruvi"), and
# each one triggers its own network call to the search API below. Those
# calls don't necessarily finish in the order they were sent - if an
# earlier, shorter query (e.g. "Kur") happens to resolve to zero results
# and its answer reaches Telegram AFTER the answer for the final, real
# query ("Kuruvi", which does have matches), Telegram displays that
# leftover "❌ No Results Found" switch_pm banner stacked on top of the
# already-shown real results.
#
# Fix: remember only the LATEST query event per user, and make EVERY query
# (including the empty-query "type a title" prompt, which used to answer
# instantly with no wait at all) sit through a short DEBOUNCE_SECONDS pause
# before doing anything. If a newer query arrives for that user during the
# pause, the older one notices when it wakes up and does nothing at all -
# not even the instant empty-query reply - so a fast, empty-query answer
# for an earlier keystroke can never win the display race against a real
# search for what the user has since finished typing. The same staleness
# check is re-tested after the network search too, since that can also
# take real time.
# ---------------------------------------------------------------------------
DEBOUNCE_SECONDS = 0.4

_latest_query_token = {}  # user_id -> opaque token identifying their latest query


def _start_query(user_id):
    """Register a new inline query as the latest for this user and return
    its token. Pass user_id=None (no from_user on the event) to skip
    tracking entirely - the staleness check below then always passes."""
    if user_id is None:
        return None
    token = object()
    _latest_query_token[user_id] = token
    return token


def _is_stale(user_id, token):
    """True if a newer inline query has arrived for this user since
    `token` was issued - meaning this in-flight search's answer should be
    dropped rather than sent to Telegram."""
    if user_id is None:
        return False
    return _latest_query_token.get(user_id) is not token


def _track_search():
    """✅ NEW - /stats command: fire-and-forget bump of the all-time
    "Total Searches" counter, called once a real search has actually
    settled (past the debounce + staleness checks). Runs as a background
    task so a slow/failed DB write never delays the inline results the
    user is waiting on; any failure is swallowed the same way the rest of
    this file swallows non-critical errors.
    """
    async def _bump():
        try:
            await increment_search_count()
        except Exception as e:
            print("⚠️ Could not increment search counter (continuing anyway)")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {e}")

    asyncio.create_task(_bump())


def _parse_mode(raw_query):
    """The Home menu's search/posters buttons (keyboards/home.py) pre-fill
    '@<BotUsername> imdb ' / '@<BotUsername> tmdb ' /
    '@<BotUsername> posters ' into the chat's inline query box - this is
    the only signal this single handler gets about which button was
    tapped, since Telegram's inline query event carries just the text the
    user typed, not which button produced it. Typing '@<BotUsername>
    <text>' directly, with no recognized prefix, defaults to IMDb.

    "posters" mode searches the same TMDb backend as "tmdb" mode (⬇️
    DOWNLOAD POSTERS reuses the exact SEARCH - TMDb search workflow) - only
    what happens after a result is picked differs, see POSTERS_ID_PREFIX
    above.
    """
    text = raw_query.strip()
    lowered = text.lower()

    if lowered.startswith("posters"):
        return "posters", text[7:].strip()
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
    user_id = inline_query.from_user.id if inline_query.from_user else None
    token = _start_query(user_id)

    # Debounce: wait a moment before acting on this query at all. If a
    # newer query arrives for this user in the meantime, this one is
    # superseded - skip it entirely (not even the instant "type a title"
    # reply below) so only the LAST query in a fast-typing burst ever gets
    # answered. See the module-level comment above for why this matters.
    await asyncio.sleep(DEBOUNCE_SECONDS)
    if _is_stale(user_id, token):
        return

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

    search_fn = search_titles_tmdb if mode in ("tmdb", "posters") else search_titles

    # Blocking HTTP request - run off the event loop so the bot can keep
    # handling other updates while it's in flight.
    results_data = await asyncio.to_thread(search_fn, query)

    # Re-check after the network call too, since that also takes real time
    # and a newer query could have arrived while it was in flight.
    if _is_stale(user_id, token):
        return

    # ✅ NEW - /stats command: this query made it all the way to a real,
    # settled search (past debounce + both staleness checks) - count it,
    # whether or not it actually found anything.
    _track_search()

    if not results_data:
        # ✅ Simple, unambiguous message when nothing matches - shown as
        # the inline "switch to PM" suggestion, since Telegram inline
        # queries have no other way to show a plain empty-state message.
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
            switch_pm_text="❌ No Results Found",
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

        if mode == "posters":
            # ⬇️ DOWNLOAD POSTERS - the result id itself carries the
            # POSTERS_ID_PREFIX marker (not just the button's callback_data)
            # so inline_result_chosen() below can tell a posters-mode pick
            # apart from a normal search pick via chosen.result_id alone,
            # since that's ALL Telegram hands back when inline feedback is
            # enabled (see that handler's docstring).
            result_id = f"{POSTERS_ID_PREFIX}{item_id}"
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    "⬇️ Download Posters", callback_data=f"{POSTERS_ID_PREFIX}{item_id}"
                )]]
            )
        else:
            result_id = item_id
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton("ℹ️ View Details", callback_data=f"sr_{item_id}")]]
            )

        if poster and poster != "N/A":
            answers.append(
                InlineQueryResultPhoto(
                    id=result_id,
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
                    id=result_id,
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(caption),
                    reply_markup=buttons,
                )
            )

    # Same staleness check as above, re-tested since the loop building
    # `answers` (and the earlier search call) both took real time - a newer
    # query could have arrived in the meantime.
    if _is_stale(user_id, token):
        return

    await inline_query.answer(
        results=answers,
        cache_time=30,
        is_personal=True,
    )


@Client.on_chosen_inline_result()
async def inline_result_chosen(client: Client, chosen: ChosenInlineResult):
    """Fires the instant a user taps one of the inline results above.

    For SEARCH - IMDb / SEARCH - TMDb results: turns that short "via
    @BotName" card straight into the full details page (poster + full
    info + Watchlist/Search Another/Done buttons) by editing it in place -
    no separate "View Details" tap required.

    For ⬇️ DOWNLOAD POSTERS results (result id carries POSTERS_ID_PREFIX,
    see the loop above): does NOT auto-send anything here. The card stays
    exactly as inserted - poster thumbnail + title/year caption + the
    "⬇️ Download Posters" button - and posters are only fetched and sent
    once the user actually taps that button (handled entirely by
    plugins/callback.py's "dp_" branch, which calls
    plugins/posters.py's send_posters()). This is the ONLY path that
    sends posters for this feature; being "chosen" from the inline result
    list is just how the card with the button gets into the chat, it's
    not itself a request to download anything yet.

    IMPORTANT: this requires inline feedback to be enabled for the bot -
    in @BotFather run /setinlinefeedback, pick this bot, and set it to
    100%. Without that, Telegram will not reliably report chosen results
    and this handler won't fire at all for SEARCH - IMDb / SEARCH - TMDb
    (the "ℹ️ View Details" button on the card stays as the fallback in
    that case, same as always - see plugins/callback.py's "sr_" branch).
    DOWNLOAD POSTERS results are unaffected either way, since they never
    act on the chosen-result event in the first place.
    """
    # The result id was set to the title's item_id (IMDb id or TMDb key),
    # or POSTERS_ID_PREFIX + that key for a DOWNLOAD POSTERS result, when
    # the card was built above.
    result_id = chosen.result_id

    # inline_message_id is only present when the bot can edit the message
    # it just caused Telegram to insert (requires inline feedback to be
    # enabled, see note above). Nothing to edit otherwise.
    if not result_id or not chosen.inline_message_id:
        return

    # ⬇️ DOWNLOAD POSTERS results: nothing to do here - see docstring
    # above. Posters are sent only when the "⬇️ Download Posters" button
    # is tapped (plugins/callback.py's "dp_" branch).
    if result_id.startswith(POSTERS_ID_PREFIX):
        return

    user_id = chosen.from_user.id if chosen.from_user else None

    await send_imdb_details_inline(
        client, chosen.inline_message_id, result_id, user_id=user_id
    )
