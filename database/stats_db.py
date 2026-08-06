# Location: database/stats_db.py  (NEW FILE)

from datetime import datetime, timezone

from database.mongo import db, users_collection, bot_state_collection

# ---------------------------------------------------------------------------
# ✅ NEW - /stats command
#
# Backs the /stats command (plugins/stats.py) with these numbers:
#   • Total Users      - users_collection document count
#   • New Users Today  - users_collection docs whose joined_at falls on
#                         today's UTC calendar day (see database/users_db.py)
#   • Total Searches   - a single running counter in bot_state_collection,
#                         bumped once per completed search across every
#                         user/chat (see increment_search_count() below and
#                         its call site in plugins/inline.py)
#   • Used/Free Storage - MongoDB's own dbStats command, measured against
#                         MONGO_STORAGE_LIMIT_MB (config.py)
# ---------------------------------------------------------------------------

# bot_state_collection already holds one other state doc
# ("monthly_watched_report" - see services/monthly_report.py); this is a
# second, unrelated one that just holds a running counter.
SEARCH_COUNTER_ID = "search_counter"


async def increment_search_count():
    """Atomically bump the all-time, all-users search counter by 1.

    Called from plugins/inline.py right after a real (debounced, settled)
    inline search actually runs - NOT once per keystroke. Telegram fires a
    fresh inline query on every keystroke, but plugins/inline.py's own
    debounce/staleness guard already collapses a fast-typing burst down to
    one real search, so this ends up counting actual searches performed,
    not raw keystrokes.
    """
    await bot_state_collection.update_one(
        {"_id": SEARCH_COUNTER_ID},
        {"$inc": {"count": 1}},
        upsert=True,
    )


async def get_total_searches():
    """Return the all-time, all-users search counter (0 if none yet)."""
    doc = await bot_state_collection.find_one({"_id": SEARCH_COUNTER_ID})
    return doc.get("count", 0) if doc else 0


async def get_total_users():
    """Return the total number of registered users (database/users_db.py's
    register_user(), fired from /start)."""
    return await users_collection.count_documents({})


async def get_new_users_today():
    """Return how many users first started the bot today (UTC calendar
    day), using each user's joined_at (database/users_db.py)."""
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return await users_collection.count_documents(
        {"joined_at": {"$gte": start_of_day}}
    )


async def get_storage_stats(limit_mb):
    """Return (used_mb, free_mb) for the bot's MongoDB database, measured
    against `limit_mb` (e.g. MongoDB Atlas' free-tier 512 MB cap - see
    config.MONGO_STORAGE_LIMIT_MB), using MongoDB's own dbStats command.
    """
    stats = await db.command("dbStats")

    # storageSize = data on disk (compressed); indexSize = all index data.
    # Together these are what actually counts against Atlas' storage quota
    # - dataSize alone under-counts, since it reports the *uncompressed*
    # size rather than what's actually occupying the quota.
    storage_size = stats.get("storageSize", 0)
    index_size = stats.get("indexSize", 0)
    used_bytes = storage_size + index_size

    used_mb = used_bytes / (1024 * 1024)
    free_mb = max(limit_mb - used_mb, 0)

    return used_mb, free_mb
