# ✅ Import series_details as well
from services.details import movie_details, series_details

# ✅ NEW: OMDb-based lookup + formatter, used by Find Movies / Watchlist (Feature 2 & 3)
from services.omdb import get_details
from utils.formatter import format_omdb_details
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

IMAGE_URL = "https://image.tmdb.org/t/p/w500"

def get_movie_caption(movie):
    title = movie.get("title", "Unknown")
    rating = movie.get("vote_average", "N/A")
    release = movie.get("release_date", "-")
    overview = movie.get("overview", "No overview available.")

    genres = ", ".join(
        genre["name"] for genre in movie.get("genres", [])
    )

    caption = (
        f"🎬 **{title}**\n\n"
        f"⭐ Rating : {rating}\n"
        f"📅 Release : {release}\n"
        f"🎭 Genres : {genres}\n\n"
        f"📝 {overview}"
    )

    poster = movie.get("poster_path")
    if poster:
        poster = IMAGE_URL + poster

    return poster, caption

# ✅ NEW FUNCTION: Format series details with seasons/episodes
def get_series_caption(series):
    """Format TV series details including number of seasons and episodes"""
    title = series.get("name", "Unknown")
    rating = series.get("vote_average", "N/A")
    release = series.get("first_air_date", "-")
    overview = series.get("overview", "No overview available.")
    
    # ✅ Get number of seasons and episodes
    num_seasons = series.get("number_of_seasons", "N/A")
    num_episodes = series.get("number_of_episodes", "N/A")

    genres = ", ".join(
        genre["name"] for genre in series.get("genres", [])
    )

    caption = (
        f"📺 **{title}**\n\n"
        f"⭐ Rating : {rating}\n"
        f"📅 First Air : {release}\n"
        f"🎭 Genres : {genres}\n"
        f"📊 Seasons : {num_seasons}\n"      # ✅ NEW
        f"📺 Episodes : {num_episodes}\n"   # ✅ NEW
        f"\n📝 {overview}"
    )

    poster = series.get("poster_path")
    if poster:
        poster = IMAGE_URL + poster

    return poster, caption

def get_movie_info(movie_id):
    movie = movie_details(movie_id)
    if not movie:
        return None, None
    return get_movie_caption(movie)

# ✅ NEW FUNCTION: Get series info
def get_series_info(series_id):
    """Fetch and format TV series information"""
    series = series_details(series_id)
    if not series:
        return None, None
    return get_series_caption(series)


# ---------------------------------------------------------------------------
# ✅ NEW: Feature 2 & 3 - Rich OMDb details page + Trailer / Watchlist buttons
# Used by both the "Find Movies" search results and the "/watchlist" listing.
# ---------------------------------------------------------------------------

async def send_omdb_details(client, chat_id, imdb_id, in_watchlist=False):
    """Fetch full OMDb details for imdb_id and send a rich details message
    with Poster, full info caption, and 🎬 Trailer / watchlist action buttons.

    `in_watchlist` controls which watchlist button is shown:
    - False (default): this details page was opened from a search result
      (Find Movies / inline search), so it shows ❤️ Add to Watchlist
      (callback_data="addwl_<imdb_id>").
    - True: this details page was opened from the user's own Watchlist
      (tapping a number under /watchlist), so it shows
      🗑 Delete from Watchlist (callback_data="delwl_<imdb_id>") instead -
      handled in plugins/callback.py, which removes the title from the
      database, deletes this message, and refreshes the watchlist listing.
    """
    details = get_details(imdb_id)

    if not details:
        await client.send_message(chat_id, "❌ Could not find details for this title.")
        return

    caption = format_omdb_details(details)

    poster = details.get("Poster")
    poster = poster if poster and poster != "N/A" else None

    if in_watchlist:
        watchlist_button = InlineKeyboardButton(
            "🗑 Delete from Watchlist", callback_data=f"delwl_{imdb_id}"
        )
    else:
        watchlist_button = InlineKeyboardButton(
            "❤️ Add to Watchlist", callback_data=f"addwl_{imdb_id}"
        )

    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎬 Trailer", callback_data=f"trailer_{imdb_id}")],
            [watchlist_button],
        ]
    )

    try:
        if poster:
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
