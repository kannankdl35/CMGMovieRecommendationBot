from database.genres import MOVIE_GENRES
from services.tmdb import discover_movies


def get_movie_recommendations(genre, language, rating, page=1):
    """
    Returns the top movie recommendations.
    """

    genre_id = MOVIE_GENRES.get(genre)

    if not genre_id:
        return []

    response = discover_movies(
        genre_id=genre_id,
        language=language,
        rating=rating,
        page=page
    )

    if not response:
        return []

    return response.get("results", [])
