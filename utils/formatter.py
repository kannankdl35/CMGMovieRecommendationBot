def format_movies(results):
    """
    Format the top 10 movie results.
    """

    if not results:
        return "❌ No movies found."

    text = "🎬 **Top 10 Recommended Movies**\n\n"

    for index, movie in enumerate(results[:10], start=1):

        title = movie.get("title", "Unknown")
        year = movie.get("release_date", "----")[:4]
        rating = movie.get("vote_average", "N/A")

        text += (
            f"{index}. **{title}** ({year})\n"
            f"⭐ {rating}\n\n"
        )

    return text
