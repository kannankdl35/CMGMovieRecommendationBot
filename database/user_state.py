# Location: database/user_state.py  (REPLACE ENTIRE FILE)

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


# ---------- 🗓️ This Month Watched listing message tracking ----------
# ✅ NEW: Same pattern as the Watchlist's set_last_watchlist_message() above -
# remembers the (chat_id, message_id) of the last "This Month Watched"
# listing shown to a user, so a fresh open or a refresh after add/delete
# removes the previous listing instead of leaving duplicates stacked in
# the chat.

def set_last_month_watched_message(user_id: int, chat_id: int, message_id: int):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id]["month_watched_msg"] = (chat_id, message_id)


def get_last_month_watched_message(user_id: int):
    return user_states.get(user_id, {}).get("month_watched_msg")


def clear_last_month_watched_message(user_id: int):
    if user_id in user_states:
        user_states[user_id].pop("month_watched_msg", None)


# ---------- ✏️ Custom Caption input tracking ----------
# ✅ NEW: Remembers which source ("imdb"/"tmdb"), if any, a user is
# currently expected to send their next custom caption template for - set
# when they open "✏️ Custom Caption" under IMDb/TMDb Settings
# (plugins/callback.py), read by plugins/custom_caption.py's plain-text
# message handler, and cleared either once that message arrives or as
# soon as the user taps any other button (see the top of
# plugins/callback.py's callback_handler()).

def set_awaiting_custom_caption(user_id: int, source: str):
    set_state(user_id, "awaiting_custom_caption", source)


def get_awaiting_custom_caption(user_id: int):
    return get_state(user_id).get("awaiting_custom_caption")


def clear_awaiting_custom_caption(user_id: int):
    if user_id in user_states:
        user_states[user_id].pop("awaiting_custom_caption", None)
