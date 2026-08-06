# Location: database/month_watched_db.py  (NEW FILE)

from collections import Counter
from datetime import datetime, timezone

from database.mongo import month_watched_collection
from utils.achievements import build_achievement_progress

# ---------------------------------------------------------------------------
# ✅ NEW - "This Month Watched" feature (Features 1, 3, 4, 5)
#
# Structure per document: user_id, imdb_id (real IMDb id OR a TMDb key like
# "tmdb_movie_603" - same key_id used everywhere else in the bot, see
# plugins/details.py), title, poster, year, media_type, genre, language,
# rating, runtime_minutes, month_key ("YYYY-MM", UTC), date_added.
#
# `month_key` is the whole trick behind the monthly reset (Feature 5): every
# query in this file is scoped to a month_key, so a new calendar month
# automatically starts from zero without deleting anything - last month's
# documents just stop being the ones any "current month" query returns.
# ---------------------------------------------------------------------------

_indexes_ready = False


async def _ensure_indexes():
    """A user can only mark the same title watched once per calendar month
    (they can mark it again next month - a fresh document with a new
    month_key)."""
    global _indexes_ready

    if _indexes_ready:
        return

    await month_watched_collection.create_index(
        [("user_id", 1), ("imdb_id", 1), ("month_key", 1)],
        unique=True,
    )

    _indexes_ready = True


def current_month_key(dt=None):
    """'YYYY-MM' for the given datetime (defaults to now, UTC). The bot has
    no per-user timezone info, so every user's "month" is the same UTC
    calendar month."""
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m")


def month_key_to_label(month_key):
    """Turn a 'YYYY-MM' month_key into a human-readable label, e.g.
    "2026-08" -> "August 2026". Used to show the current month's name in
    the "This Month Watched" / "Monthly Status" headers (see
    plugins/month_watched.py), so it always matches whatever month_key the
    stats were actually computed for and updates automatically every
    calendar month - no hardcoding needed."""
    try:
        return datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
    except (TypeError, ValueError):
        return month_key


def _clean(value):
    if not value or value == "N/A":
        return None
    return value


def _parse_rating(details):
    raw = _clean(details.get("imdbRating"))
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_runtime_minutes(details):
    raw = _clean(details.get("Runtime"))
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else None


def _parse_language(details):
    raw = _clean(details.get("Language"))
    if not raw:
        return None
    # Some sources report a comma list ("EN, FR") - keep just the first as
    # this title's "main" language for the Explorer achievement / Top
    # Language stat.
    return raw.split(",")[0].strip() or None


def _parse_genre(details):
    return _clean(details.get("Genre"))


async def add_to_month_watched(user_id, key_id, details):
    """Save a movie/series to the user's CURRENT month watched list.
    `details` is the dict returned by plugins/details.py's fetch_details() -
    reused here instead of re-fetching or duplicating IMDb/TMDb parsing
    logic.

    Returns True if newly added, False if it was already marked watched
    this month (prevents duplicate entries).
    """
    await _ensure_indexes()

    month_key = current_month_key()

    existing = await month_watched_collection.find_one(
        {"user_id": user_id, "imdb_id": key_id, "month_key": month_key}
    )

    if existing:
        return False

    poster = _clean(details.get("Poster"))
    year = _clean(details.get("Year"))

    document = {
        "user_id": user_id,
        "imdb_id": key_id,
        "title": details.get("Title") or "Unknown",
        "poster": poster,
        "year": year,
        "media_type": details.get("Type", "movie"),
        "genre": _parse_genre(details),
        "language": _parse_language(details),
        "rating": _parse_rating(details),
        "runtime_minutes": _parse_runtime_minutes(details),
        "month_key": month_key,
        "date_added": datetime.now(timezone.utc),
    }

    await month_watched_collection.insert_one(document)
    return True


async def remove_from_month_watched(user_id, key_id, month_key=None):
    """Delete a single This Month Watched entry (current month by default).
    Returns True if a document was actually removed."""
    if month_key is None:
        month_key = current_month_key()

    result = await month_watched_collection.delete_one(
        {"user_id": user_id, "imdb_id": key_id, "month_key": month_key}
    )
    return result.deleted_count > 0


async def is_in_month_watched(user_id, key_id, month_key=None):
    if month_key is None:
        month_key = current_month_key()

    doc = await month_watched_collection.find_one(
        {"user_id": user_id, "imdb_id": key_id, "month_key": month_key}
    )
    return doc is not None


async def get_month_watched(user_id, month_key=None):
    """All of a user's This Month Watched entries for one month (current
    month by default), in the order they were added."""
    if month_key is None:
        month_key = current_month_key()

    cursor = month_watched_collection.find(
        {"user_id": user_id, "month_key": month_key}
    ).sort("date_added", 1)

    return await cursor.to_list(length=500)


def build_stats_from_docs(docs, month_key):
    """Pure function: turn a list of This Month Watched documents into the
    Monthly Status numbers + the 7 achievements' progress. Shared by the
    live "This Month Watched" page (plugins/month_watched.py) and the
    end-of-month report (services/monthly_report.py) so both always agree.

    Only movies count toward achievements / Movie Watch Time - series are
    counted for "Series Watched" only.
    """
    movies = [d for d in docs if d.get("media_type") != "series"]
    series = [d for d in docs if d.get("media_type") == "series"]

    movie_minutes = sum(d.get("runtime_minutes") or 0 for d in movies)

    year_of_month = month_key.split("-")[0]
    fresh_release_count = sum(
        1 for d in movies if d.get("year") and str(d.get("year")) == year_of_month
    )

    movie_languages = {d["language"] for d in movies if d.get("language")}

    movie_genres = set()
    for d in movies:
        genre = d.get("genre")
        if genre:
            for part in genre.split(","):
                part = part.strip()
                if part:
                    movie_genres.add(part)

    quality_count = sum(
        1 for d in movies if (d.get("rating") is not None and d.get("rating") >= 7.0)
    )

    # Top Genre / Top Language consider everything watched this month
    # (movies AND series), unlike the achievements above.
    genre_counter = Counter()
    language_counter = Counter()

    for d in docs:
        genre = d.get("genre")
        if genre:
            for part in genre.split(","):
                part = part.strip()
                if part:
                    genre_counter[part] += 1

        language = d.get("language")
        if language:
            language_counter[language] += 1

    top_genre = genre_counter.most_common(1)[0][0] if genre_counter else None
    top_language = language_counter.most_common(1)[0][0] if language_counter else None

    achievements = build_achievement_progress(
        movie_count=len(movies),
        fresh_release_count=fresh_release_count,
        language_count=len(movie_languages),
        genre_count=len(movie_genres),
        quality_count=quality_count,
        movie_hours=movie_minutes / 60,
    )

    unlocked_count = sum(1 for a in achievements if a["unlocked"])

    return {
        "docs": docs,
        "month_key": month_key,
        "movie_count": len(movies),
        "series_count": len(series),
        "movie_minutes": movie_minutes,
        "movie_hours": movie_minutes / 60,
        "movie_days": movie_minutes / 60 / 24,
        "top_genre": top_genre,
        "top_language": top_language,
        "achievements": achievements,
        "unlocked_count": unlocked_count,
    }


async def compute_monthly_stats(user_id, month_key=None):
    """Fetch + compute this user's stats for one month (current month by
    default). Used by the live page and the end-of-month report alike."""
    if month_key is None:
        month_key = current_month_key()

    docs = await get_month_watched(user_id, month_key)
    return build_stats_from_docs(docs, month_key)
