from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.imdb import get_details


def _clean(value):
    """The IMDb API (services/imdb.py) leaves unavailable fields as None -
    treat that the same as missing so it's skipped instead of printed."""
    if not value or value == "N/A":
        return None
    return value


async def send_result_cards(client, chat_id, items, callback_prefix):
    """Send a list of movie/series cards (poster + title/year + details button).

    `items` is a list of dicts with keys: Title, Year, Poster, imdbID.
    Used for Find Movies search results (Feature 1) where the user still
    needs a way to drill into the full details/trailer/add-to-watchlist page.

    CHANGED: Each card's caption now also shows Language and Release Date
    (via a per-title IMDb API lookup) instead of just the media type + title +
    year, matching the inline search cards in plugins/inline.py (Feature 4
    fix). The media type label (📺 Series vs 🎬 Movie) is also resolved from
    that same lookup, since the IMDb API's search endpoint doesn't report a
    type up front the way OMDb's did.
    """
    for item in items:
        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        poster = item.get("Poster")
        imdb_id = item.get("imdbID")

        # Best-effort enrichment - failures here just mean the extra two
        # lines (and the movie/series label) fall back to defaults, never
        # that the card fails to send.
        details = get_details(imdb_id) if imdb_id else None

        media_type = details.get("Type", "movie") if details else "movie"
        label = "📺 Series" if media_type == "series" else "🎬 Movie"
        caption = f"{label}\n**{title}** ({year})"

        if details:
            release_date = _clean(details.get("Year"))
            language = _clean(details.get("Language"))

            if release_date:
                caption += f"\n📅 Release : {release_date}"
            if language:
                caption += f"\n🗣 Language : {language}"

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("ℹ️ View Details", callback_data=f"{callback_prefix}{imdb_id}")]]
        )

        try:
            if poster and poster != "N/A":
                await client.send_photo(
                    chat_id=chat_id,
                    photo=poster,
                    caption=caption,
                    reply_markup=buttons
                )
            else:
                await client.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_markup=buttons
                )
        except Exception:
            # Fallback to text if the poster URL fails to load as a photo
            await client.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=buttons
            )
                
