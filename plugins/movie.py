from database.user_state import set_state, get_state, clear_state

from services.discover import get_movie_recommendations

from utils.formatter import format_movies


def set_movie_type(user_id):
    set_state(user_id, "type", "movie")


def save_genre(user_id, genre):
    set_state(user_id, "genre", genre)


def save_language(user_id, language):
    set_state(user_id, "language", language)


def save_rating(user_id, rating):
    set_state(user_id, "rating", rating)


def reset(user_id):
    clear_state(user_id)


def recommendations(user_id):

    state = get_state(user_id)

    results = get_movie_recommendations(
        genre=state.get("genre"),
        language=state.get("language"),
        rating=state.get("rating"),
    )

    text = format_movies(results)

    return text, results
