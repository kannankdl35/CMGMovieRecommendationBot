# Temporary in-memory user state
# Later can be moved to MongoDB

user_states = {}


def set_state(user_id: int, key: str, value):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id][key] = value


def get_state(user_id: int):
    return user_states.get(user_id, {})


def clear_state(user_id: int):
    user_states.pop(user_id, None)


# ---------- Recommendation Results ----------

def save_results(user_id: int, results):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id]["results"] = results


def get_results(user_id: int):
    return user_states.get(user_id, {}).get("results", [])


def clear_results(user_id: int):
    if user_id in user_states:
        user_states[user_id].pop("results", None)


# ---------- Watchlist listing message tracking ----------
# ✅ NEW: Remembers the (chat_id, message_id) of the last watchlist listing
# message shown to a user, so a fresh /watchlist or a refresh after
# add/delete can remove the previous listing instead of leaving duplicates
# stacked in the chat.

def set_last_watchlist_message(user_id: int, chat_id: int, message_id: int):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id]["watchlist_msg"] = (chat_id, message_id)


def get_last_watchlist_message(user_id: int):
    return user_states.get(user_id, {}).get("watchlist_msg")


def clear_last_watchlist_message(user_id: int):
    if user_id in user_states:
        user_states[user_id].pop("watchlist_msg", None)


# ---------- 🔥 Trending Now results tracking ----------
# Remembers the last "Today"/"This Week" trending listing fetched for a
# user, so the numbered buttons under it (keyboards/trending.py's
# trending_list_keyboard()) can be mapped back to a title without
# re-querying TMDb - button "3" means "the 3rd item in this list", the
# same pattern database/watchlist_db.py + keyboards/watchlist.py use for
# the Watchlist's own numbered buttons.

def save_trending_results(user_id: int, results):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id]["trending_results"] = results


def get_trending_results(user_id: int):
    return user_states.get(user_id, {}).get("trending_results", [])


def clear_trending_results(user_id: int):
    if user_id in user_states:
        user_states[user_id].pop("trending_results", None)


# ---------- 🎲 Suggest Random Movie results tracking ----------
# Remembers the last random-movie listing fetched for a user, keyed by
# language, so the numbered buttons under it
# (keyboards/random_movies.py's random_list_keyboard()) can be mapped back
# to a title without re-querying TMDb - same pattern as
# save_trending_results()/get_trending_results() above. Keyed by language
# (rather than a single slot) so switching languages doesn't invalidate a
# listing the user might tap "🔙 Back" into again later.

def save_random_results(user_id: int, lang: str, results):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id].setdefault("random_results", {})[lang] = results


def get_random_results(user_id: int, lang: str):
    return user_states.get(user_id, {}).get("random_results", {}).get(lang, [])


def clear_random_results(user_id: int):
    if user_id in user_states:
        user_states[user_id].pop("random_results", None)
