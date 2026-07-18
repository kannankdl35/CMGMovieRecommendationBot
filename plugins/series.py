from database.user_state import set_state, get_state, clear_state

from services.discover import get_series_recommendations

from utils.formatter import format_movies


def set_series_type(user_id):
    set_state(user_id, "type", "series")


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

    results = get_series_recommendations(
        genre=state.get("genre"),
        language=state.get("language"),
        rating=state.get("rating"),
    )

    # ✅ NEW (Feature 6): show the selected Genre / Language / IMDb Rating
    # at the top of the results list.
    text = format_movies(
        results,
        genre=state.get("genre"),
        language=state.get("language"),
        rating=state.get("rating"),
    )

    return text, results
