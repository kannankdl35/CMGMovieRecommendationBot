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
