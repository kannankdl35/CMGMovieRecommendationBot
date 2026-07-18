from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def send_result_cards(client, chat_id, items, callback_prefix):
    """Send a list of movie/series cards (poster + title/year + details button).

    `items` is a list of dicts with keys: Title, Year, Poster, imdbID, Type.
    Shared between Find Movies search results and the /watchlist listing
    to avoid duplicate code (used for Feature 1 and Feature 4).
    """
    for item in items:
        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        poster = item.get("Poster")
        imdb_id = item.get("imdbID")
        media_type = item.get("Type", "movie")

        label = "📺 Series" if media_type == "series" else "🎬 Movie"
        caption = f"{label}\n**{title}** ({year})"

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
            # ✅ Fallback to text if the poster URL fails to load as a photo
            await client.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=buttons
            )
