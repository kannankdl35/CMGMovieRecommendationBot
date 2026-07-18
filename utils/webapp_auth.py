"""
✅ NEW: Telegram Mini App (Web App) auth helper.

Every request the Mini App front-end makes to our API includes the raw
`initData` string that Telegram signs and injects into the Web App via
`Telegram.WebApp.initData`. We must verify that signature ourselves before
trusting the `user` it contains - otherwise anyone could call the API and
claim to be any Telegram user id.

Verification algorithm (per Telegram's Web Apps docs):
1. Parse initData as a query string.
2. Pull out `hash`, remove it from the data.
3. Sort the remaining key=value pairs, join with "\n".
4. secret_key = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
5. computed_hash = HMAC_SHA256(key=secret_key, msg=data_check_string)
6. computed_hash (hex) must equal the `hash` field.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from config import BOT_TOKEN

# initData older than this is rejected (seconds). Telegram recommends ~1 day.
MAX_INIT_DATA_AGE = 86400


def _build_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str):
    """Validate a Telegram Web App `initData` string.

    Returns the parsed dict of fields (with `user` already json-decoded)
    if valid, or None if the signature is missing/invalid/expired.
    """
    if not init_data:
        return None

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(parsed.items())
    )

    secret_key = _build_secret_key(BOT_TOKEN)
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # ✅ Reject stale initData (protects against replayed requests)
    auth_date = parsed.get("auth_date")
    if auth_date:
        try:
            if time.time() - int(auth_date) > MAX_INIT_DATA_AGE:
                return None
        except ValueError:
            pass

    if "user" in parsed:
        try:
            parsed["user"] = json.loads(parsed["user"])
        except (json.JSONDecodeError, TypeError):
            return None

    return parsed


def get_user_id_from_init_data(init_data: str):
    """Convenience wrapper: returns the Telegram user id or None."""
    data = validate_init_data(init_data)
    if not data or "user" not in data:
        return None
    return data["user"].get("id")
