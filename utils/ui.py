from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.omdb import get_details


def _clean(value):
    """OMDb uses the literal string 'N/A' for missing fields - treat that
    the same as missing so it's skipped instead of printed as 'N/A'."""
    if not value or value == "N/A":
        return None
    return value


async def send_result_cards(client, chat_id, items, callback_prefix):
    """Send a list of movie/series cards (poster + title/year + details button).

    `items` is a list of dicts with keys: Title, Year, Poster, imdbID, Type.
    Used for Find Movies search results (Feature 1) where the user still
    needs a way to drill into the full details/trailer/add-to-watchlist page.

    CHANGED: Each card's caption now also shows Language and Release Date
    (via a per-title OMDb lookup) instead of just the media type + title +
    year, matching the inline search cards in plugins/inline.py (Feature 4
    fix).
    """
    for item in items:
        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        poster = item.get("Poster")
        imdb_id = item.get("imdbID")
        media_type = item.get("Type", "movie")

        label = "📺 Series" if media_type == "series" else "🎬 Movie"
        caption = f"{label}\n**{title}** ({year})"

        # Best-effort enrichment - failures here just mean the extra two
        # lines are skipped, never that the card fails to send.
        details = get_details(imdb_id) if imdb_id else None
        if details:
            release_date = _clean(details.get("Released"))
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
