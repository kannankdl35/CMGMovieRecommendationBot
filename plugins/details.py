# ✅ Import series_details as well
from services.details import movie_details, series_details

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
