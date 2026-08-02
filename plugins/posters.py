# Location: plugins/posters.py  (REPLACE ENTIRE FILE)

import asyncio

from pyrogram.types import InputMediaPhoto

from services.tmdb import fetch_posters_tmdb

# Telegram's sendMediaGroup hard limit is 10 items per group - this is also
# the feature spec's own cap ("only 10 posters"), so one call covers both.
MAX_POSTERS = 10


async def send_posters(client, chat_id, key_id):
    """⬇️ DOWNLOAD POSTERS - fetch up to MAX_POSTERS (10) posters TMDb has
    on file for `key_id` (a TMDb-sourced key, "tmdb_movie_603" /
    "tmdb_tv_1396" - see services/tmdb.py's search_titles_tmdb()) and send
    them together as a SINGLE Telegram media group (album): no caption, no
    inline buttons, no title/overview/cast/rating/etc. text of any kind -
    just the posters themselves, at TMDb's highest available resolution
    ("original" size, see fetch_posters_tmdb()).

    If `key_id` isn't a TMDb key (e.g. this ever got called with a plain
    IMDb id) or TMDb has no posters on file for it, sends a single
    friendly "no posters" message instead. If TMDb has only one poster on
    file, that one is sent as a plain photo (Telegram's media group
    requires at least 2 items).

    Called from:
    - plugins/inline.py's inline_result_chosen(), when a DOWNLOAD POSTERS
      inline search result is chosen (requires inline feedback enabled).
    - plugins/callback.py's "dp_" callback handler, the fallback path for
      when inline feedback isn't enabled (same pattern as the "sr_"/
      View Details fallback for the regular search flow).
    """
    if not key_id or not key_id.startswith("tmdb_"):
        await client.send_message(chat_id, "❌ Could not find this title.")
        return

    poster_urls = await asyncio.to_thread(fetch_posters_tmdb, key_id)

    if not poster_urls:
        await client.send_message(chat_id, "No posters are available for this title.")
        return

    # Cap at 10 - both Telegram's own media-group ceiling and the feature
    # spec's requested limit.
    poster_urls = poster_urls[:MAX_POSTERS]

    if len(poster_urls) == 1:
        # sendMediaGroup requires 2-10 items - a single poster just goes
        # out as a normal photo message instead.
        try:
            await client.send_photo(chat_id=chat_id, photo=poster_urls[0])
        except Exception:
            await client.send_message(chat_id, "No posters are available for this title.")
        return

    media = [InputMediaPhoto(media=url) for url in poster_urls]

    try:
        await client.send_media_group(chat_id=chat_id, media=media)
    except Exception:
        # If Telegram rejects the whole album (e.g. one bad URL in the
        # batch), fall back to sending each poster as its own message
        # rather than losing the batch entirely.
        for poster_url in poster_urls:
            try:
                await client.send_photo(chat_id=chat_id, photo=poster_url)
            except Exception:
                continue
