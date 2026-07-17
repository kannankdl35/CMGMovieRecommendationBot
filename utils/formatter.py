def format_movies(results):
    """
    Format the top 10 movie recommendations.
    """

    if not results:
        return "❌ No movies found matching your selection."

    text = (
        "🎬 **Top 10 Recommended Movies**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    for index, movie in enumerate(results[:10], start=1):

        title = (
    movie.get("title")
    or movie.get("name")
    or "Unknown"
        )
        release_date = movie.get("release_date", "")
        year = release_date[:4] if release_date else "----"

        rating = movie.get("vote_average", "N/A")

        text += (
            f"**{index}. {title} ({year})**\n"
            f"⭐ Rating: **{rating}**\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━━━━━\n"
        "Choose **More Results** to load another 10 movies."
    )

    return text
