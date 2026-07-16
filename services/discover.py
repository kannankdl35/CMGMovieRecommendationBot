from services.tmdb import discover_movies


def get_movie_recommendations(genre, language, rating):
    """
    Returns the top 10 recommended movies.
    """

    data = discover_movies(
        genre=genre,
        language=language,
        rating=rating
    )

    if not data:
        return []

    return data.get("results", [])[:10]
