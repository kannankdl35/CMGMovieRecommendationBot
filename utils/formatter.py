IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def format_movies(results):

    if not results:
        return "❌ No movies found."

    text = "🎬 **Top 10 Recommended Movies**\n\n"

    for i, movie in enumerate(results[:10], start=1):

        title = movie.get("title", "Unknown")

        year = movie.get("release_date", "")
        year = year[:4] if year else "----"

        rating = movie.get("vote_average", 0)

        overview = movie.get("overview", "")

        if len(overview) > 120:
            overview = overview[:120] + "..."

        text += (
            f"**{i}. {title} ({year})**\n"
            f"⭐ {rating}\n"
            f"📝 {overview}\n\n"
        )

    return text
