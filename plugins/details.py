from pyrogram import Client
from pyrogram.types import CallbackQuery

from services.details import movie_details

IMAGE_URL = "https://image.tmdb.org/t/p/w500"


@Client.on_callback_query()
async def details_callback(client: Client, callback: CallbackQuery):

    data = callback.data

    # Only handle movie detail callbacks
    if not data.startswith("movie_"):
        return

    movie_id = data.replace("movie_", "")

    # Ignore genre callbacks like:
    # movie_action
    # movie_comedy
    # movie_drama
    if not movie_id.isdigit():
        await callback.answer()
        return

    movie = movie_details(movie_id)

    if not movie:
        await callback.answer("Movie not found.", show_alert=True)
        return

    poster = movie.get("poster_path")

    if poster:
        poster = IMAGE_URL + poster

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

    if poster:
        await client.send_photo(
            chat_id=callback.message.chat.id,
            photo=poster,
            caption=caption
        )
    else:
        await callback.message.reply_text(caption)

    await callback.answer()
