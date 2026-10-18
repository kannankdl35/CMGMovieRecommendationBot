# Location: plugins/posters.py  (REPLACE ENTIRE FILE)

import asyncio

from pyrogram.types import InputMediaPhoto

from services.tmdb import fetch_posters_tmdb

# Telegram's sendMediaGroup hard limit is 10 items per group - this is also
# the feature spec's own cap ("only 10 posters"), so one call covers both.
MAX_POSTERS = 10

# ⬇️ DOWNLOAD POSTERS has two flavours (keyboards/posters.py's menu):
#   VERTICAL   - TMDb's portrait "posters" (2:3)
#   HORIZONTAL - TMDb's landscape "backdrops" (16:9)
VERTICAL = "vertical"
HORIZONTAL = "horizontal"

# Result-id / callback_data prefixes - the prefix itself is how
# plugins/inline.py's inline_result_chosen() and plugins/callback.py's
# download-posters branch tell WHICH orientation to fetch, since a result id
# / callback_data string is all Telegram hands back. (Keep them short:
# Telegram caps both at 64 bytes, and the TMDb key is appended after.)
POSTERS_ID_PREFIXES = {VERTICAL: "dpv_", HORIZONTAL: "dph_"}

# Cards that were sent BEFORE the vertical/horizontal split still sit in
# users' chats with the old "dp_" button - those keep working, as vertical.
LEGACY_POSTERS_ID_PREFIX = "dp_"


def build_posters_id(orientation, key_id):
    """Result id / callback_data for a DOWNLOAD POSTERS card, e.g.
    build_posters_id(HORIZONTAL, "tmdb_movie_603") -> "dph_tmdb_movie_603"."""
    prefix = POSTERS_ID_PREFIXES.get(orientation, POSTERS_ID_PREFIXES[VERTICAL])
    return f"{prefix}{key_id}"


def parse_posters_id(data):
    """Inverse of build_posters_id(). Returns (orientation, key_id) if
    `data` is a DOWNLOAD POSTERS result id / callback_data (including the
    legacy "dp_" form, which means vertical), otherwise None - so it doubles
    as the "is this a posters id?" check."""
    if not data:
        return None

    for orientation, prefix in POSTERS_ID_PREFIXES.items():
        if data.startswith(prefix):
            return orientation, data[len(prefix):]

    if data.startswith(LEGACY_POSTERS_ID_PREFIX):
        return VERTICAL, data[len(LEGACY_POSTERS_ID_PREFIX):]

    return None


async def send_posters(client, chat_id, key_id, orientation=VERTICAL):
    """⬇️ DOWNLOAD POSTERS - fetch up to MAX_POSTERS (10) posters of the
    requested `orientation` (VERTICAL or HORIZONTAL) TMDb has on file for
    `key_id` (a TMDb-sourced key, "tmdb_movie_603" / "tmdb_tv_1396" - see
    services/tmdb.py's search_titles_tmdb()) and send them together as a
    SINGLE Telegram media group (album): no caption, no inline buttons, no
    title/overview/cast/rating/etc. text of any kind - just the posters
    themselves, at TMDb's highest available resolution ("original" size,
    see fetch_posters_tmdb()).

    If `key_id` isn't a TMDb key (e.g. this ever got called with a plain
    IMDb id) or TMDb has no posters of that orientation on file for it,
    sends a single friendly "no posters" message instead. If TMDb has only
    one poster on file, that one is sent as a plain photo (Telegram's media
    group requires at least 2 items).

    Called from:
    - plugins/callback.py's download-posters callback handler (the
      "dpv_" / "dph_" / legacy "dp_" button on the card sent from a
      DOWNLOAD POSTERS inline search result).
    """
    if orientation not in POSTERS_ID_PREFIXES:
        orientation = VERTICAL

    if not key_id or not key_id.startswith("tmdb_"):
        await client.send_message(chat_id, "❌ Couldn't find this title.")
        return

    poster_urls = await asyncio.to_thread(fetch_posters_tmdb, key_id, orientation)

    if not poster_urls:
        await client.send_message(
            chat_id, f"😕 No {orientation} posters available for this title."
        )
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
            await client.send_message(
                chat_id, f"😕 No {orientation} posters available for this title."
            )
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
