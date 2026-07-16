def format_movies(results):
    if not results:
        return "❌ No movies found."

    text = "🎬 **Top 10 Recommended Movies**\n\n"

    for i, movie in enumerate(results[:10], start=1):

        title = movie.get("title", "Unknown")
        rating = movie.get("vote_average", "N/A")
        release = movie.get("release_date", "")

        year = release[:4] if release else "----"

        text += (
            f"{i}. **{title}** ({year})\n"
            f"⭐ {rating}\n\n"
        )

    return text
