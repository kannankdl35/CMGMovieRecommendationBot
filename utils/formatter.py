def format_movies(results):
    """Format the top 10 movie/series recommendations.
    Handles both movies and TV series."""

    if not results:
        return "❌ No movies found matching your selection."

    # ✅ Check if results are movies or series
    is_series = "name" in results[0] if results else False

    if is_series:
        text = (
            "📺 **Top 10 Recommended Series**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        text = (
            "🎬 **Top 10 Recommended Movies**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

    for index, item in enumerate(results[:10], start=1):
        if is_series:
            # ✅ Handle TV Series correctly
            title = item.get("name", "Unknown")  # ✅ Use "name" for series
            release_date = item.get("first_air_date", "")  # ✅ Use "first_air_date"
            year = release_date[:4] if release_date else "----"
            rating = item.get("vote_average", "N/A")
        else:
            # Handle Movies
            title = item.get("title", "Unknown")
            release_date = item.get("release_date", "")
            year = release_date[:4] if release_date else "----"
            rating = item.get("vote_average", "N/A")

        text += (
            f"**{index}. {title} ({year})**\n"
            f"⭐ Rating: **{rating}**\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━"
    return text
