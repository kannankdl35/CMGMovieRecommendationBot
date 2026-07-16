# Temporary in-memory user state
# Later we'll move this to MongoDB

user_states = {}


def set_state(user_id: int, key: str, value):
    if user_id not in user_states:
        user_states[user_id] = {}

    user_states[user_id][key] = value


def get_state(user_id: int):
    return user_states.get(user_id, {})


def clear_state(user_id: int):
    user_states.pop(user_id, None)
