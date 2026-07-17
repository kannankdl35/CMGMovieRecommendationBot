from services.details import movie_details

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


def get_movie_info(movie_id):

    movie = movie_details(movie_id)

    if not movie:
        return None, None

    return get_movie_caption(movie)
