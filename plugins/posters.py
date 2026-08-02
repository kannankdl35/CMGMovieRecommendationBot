# Location: plugins/posters.py  (NEW FILE)

import asyncio

from services.tmdb import fetch_posters_tmdb

# Telegram rejects a single sendPhoto call faster than it can process a
# long burst of them - a small delay between sends keeps this well clear of
# per-chat flood limits when a title has a lot of posters on file.
_SEND_DELAY_SECONDS = 0.3


async def send_posters(client, chat_id, key_id):
    """⬇️ DOWNLOAD POSTERS - fetch every poster TMDb has on file for
    `key_id` (a TMDb-sourced key, "tmdb_movie_603" / "tmdb_tv_1396" - see
    services/tmdb.py's search_titles_tmdb()) and send each one as a plain
    image message: no caption, no inline buttons, no title/overview/cast/
    rating/etc. text of any kind - just the poster itself, at TMDb's
    highest available resolution ("original" size, see
    fetch_posters_tmdb()).

    If `key_id` isn't a TMDb key (e.g. this ever got called with a plain
    IMDb id) or TMDb has no posters on file for it, sends a single
    friendly "no posters" message instead.

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

    for poster_url in poster_urls:
        try:
            await client.send_photo(chat_id=chat_id, photo=poster_url)
        except Exception:
            # Skip any single poster URL Telegram fails to fetch/accept
            # rather than aborting the whole batch over one bad image.
            continue
        await asyncio.sleep(_SEND_DELAY_SECONDS)
