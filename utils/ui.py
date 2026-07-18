from urllib.parse import quote

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def send_result_cards(client, chat_id, items, callback_prefix):
    """Send a list of movie/series cards (poster + title/year + details button).

    `items` is a list of dicts with keys: Title, Year, Poster, imdbID, Type.
    Used for Find Movies search results (Feature 1) where the user still
    needs a way to drill into the full details/trailer/add-to-watchlist page.
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


# ---------------------------------------------------------------------------
# ✅ NEW: Feature 4 - Watchlist card renderer with Delete / Share buttons.
# Mirrors the "IMDb search" bot UX: poster + short "Title Year" caption,
# and a Delete + Share row underneath (instead of View Details).
# ---------------------------------------------------------------------------

async def send_watchlist_cards(client, chat_id, items):
    """Render each saved watchlist item with 🗑 Delete and 🔗 Share buttons.

    `items` is a list of dicts with keys: Title, Year, Poster, imdbID, Type.
    - Delete uses callback_data "wldel_<imdbID>" (handled in plugins/callback.py)
      and removes the entry from Mongo + deletes the card from the chat.
    - Share is a plain Telegram share-sheet URL button (no callback needed) so
      the user can forward the title to any chat.
    """
    for item in items:
        title = item.get("Title", "Unknown")
        year = item.get("Year", "-")
        poster = item.get("Poster")
        imdb_id = item.get("imdbID")

        caption = f"**{title}** {year}"

        imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
        share_text = quote(f"{title} ({year})")
        share_url = f"https://t.me/share/url?url={quote(imdb_url, safe='')}&text={share_text}"

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🗑 Delete", callback_data=f"wldel_{imdb_id}"),
                    InlineKeyboardButton("🔗 Share", url=share_url),
                ]
            ]
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
