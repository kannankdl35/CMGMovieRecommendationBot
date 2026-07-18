from datetime import datetime, timezone

from database.mongo import watchlist_collection

# ✅ Feature 5 - Database
# Structure per document: user_id, imdb_id, title, poster, year, date_added

_indexes_ready = False


async def _ensure_indexes():
    """Make sure the same movie can't be saved twice for the same user."""
    global _indexes_ready

    if _indexes_ready:
        return

    await watchlist_collection.create_index(
        [("user_id", 1), ("imdb_id", 1)],
        unique=True,
    )

    _indexes_ready = True


async def add_to_watchlist(user_id, imdb_id, title, poster, year, media_type="movie"):
    """Save a movie/series to the user's watchlist.
    Returns True if newly added, False if it was already saved.
    """
    await _ensure_indexes()

    existing = await watchlist_collection.find_one(
        {"user_id": user_id, "imdb_id": imdb_id}
    )

    if existing:
        return False

    document = {
        "user_id": user_id,
        "imdb_id": imdb_id,
        "title": title,
        "poster": poster,
        "year": year,
        "media_type": media_type,
        "date_added": datetime.now(timezone.utc),
    }

    await watchlist_collection.insert_one(document)
    return True


async def get_watchlist(user_id):
    """Return all watchlist entries for a user, most recently added first."""
    cursor = watchlist_collection.find({"user_id": user_id}).sort("date_added", -1)
    return await cursor.to_list(length=200)


async def is_in_watchlist(user_id, imdb_id):
    doc = await watchlist_collection.find_one(
        {"user_id": user_id, "imdb_id": imdb_id}
    )
    return doc is not None


# ✅ NEW: Feature 4 - Remove a title from a user's watchlist (powers the
# 🗑 Delete button shown on each watchlist card).
async def remove_from_watchlist(user_id, imdb_id):
    """Delete a single watchlist entry for this user.
    Returns True if a document was actually removed, False if it wasn't
    there to begin with (e.g. double tap / already deleted)."""
    result = await watchlist_collection.delete_one(
        {"user_id": user_id, "imdb_id": imdb_id}
    )
    return result.deleted_count > 0
