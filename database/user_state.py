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
