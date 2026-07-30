# Location: database/users_db.py  (NEW FILE)

from database.mongo import users_collection

# ---------------------------------------------------------------------------
# ✅ NEW - "This Month Watched" feature (Monthly Reset & Report)
#
# A minimal record of every user who has ever started the bot. This is the
# only reliable "this person uses the bot" signal available (Telegram bots
# only ever hear from users who've messaged them), and it's what lets the
# end-of-month report (services/monthly_report.py) message EVERY registered
# user - including ones whose stats are all zero for the month - instead of
# only users who happen to have a watched-list entry.
# ---------------------------------------------------------------------------


async def register_user(user_id, username=None, first_name=None):
    """Upsert a user record. Called from plugins/start.py's /start handler.

    Safe to call every time /start is used - it just keeps username/
    first_name up to date rather than creating duplicates.
    """
    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
            }
        },
        upsert=True,
    )


async def get_all_user_ids():
    """Return the user_id of every registered user, for the monthly
    broadcast in services/monthly_report.py."""
    cursor = users_collection.find({}, {"user_id": 1})
    docs = await cursor.to_list(length=100000)
    return [doc["user_id"] for doc in docs if doc.get("user_id")]
