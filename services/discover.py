from database.genres import MOVIE_GENRES, SERIES_GENRES
from services.tmdb import discover_movies, discover_series


def get_movie_recommendations(genre, language, rating, page=1):

    genre_id = MOVIE_GENRES.get(genre)

    if genre_id is None:
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


def get_series_recommendations(genre, language, rating, page=1):

    genre_id = SERIES_GENRES.get(genre)

    if genre_id is None:
        return []

    response = discover_series(
        genre_id=genre_id,
        language=language,
        rating=rating,
        page=page
    )

    if not response:
        return []

    return response.get("results", [])
