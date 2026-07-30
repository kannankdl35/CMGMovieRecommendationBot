# Location: utils/achievements.py  (NEW FILE)

# ---------------------------------------------------------------------------
# ✅ NEW - "This Month Watched" feature: Achievements (Feature 4)
#
# Only MOVIES count toward achievement progress and Movie Watch Time -
# series watched this month are tracked (for "Series Watched" in the
# Monthly Status) but never feed into any achievement here.
#
# This module is pure/stateless: database/month_watched_db.py's
# build_stats_from_docs() gathers the raw numbers from a user's watched
# documents and calls build_achievement_progress() below to turn them into
# the 7 achievements with their progress - no DB access happens in here,
# which keeps this reusable for both the live "This Month Watched" page and
# the end-of-month report (services/monthly_report.py).
# ---------------------------------------------------------------------------

ACHIEVEMENTS = [
    {
        "key": "movie_buff",
        "icon": "🍿",
        "name": "Movie Buff",
        "criteria": "Watch 10 movies",
        "target": 10,
        "unit": "",
    },
    {
        "key": "movie_maniac",
        "icon": "🎞️",
        "name": "Movie Maniac",
        "criteria": "Watch 20 movies",
        "target": 20,
        "unit": "",
    },
    {
        "key": "fresh_release_fan",
        "icon": "🆕",
        "name": "Fresh Release Fan",
        "criteria": "Watch 5 movies released in the current year",
        "target": 5,
        "unit": "",
    },
    {
        "key": "explorer",
        "icon": "🌍",
        "name": "Explorer",
        "criteria": "Watch movies in 5 different languages",
        "target": 5,
        "unit": "",
    },
    {
        "key": "genre_explorer",
        "icon": "🎭",
        "name": "Genre Explorer",
        "criteria": "Watch movies from 7 different genres",
        "target": 7,
        "unit": "",
    },
    {
        "key": "quality_hunter",
        "icon": "⭐",
        "name": "Quality Hunter",
        "criteria": "Watch five movies rated 7.0+",
        "target": 5,
        "unit": "",
    },
    {
        "key": "cinema_addict",
        "icon": "🎬",
        "name": "Cinema Addict",
        "criteria": "Watch 75 hours of movies",
        "target": 75,
        "unit": " hours",
    },
]

TOTAL_ACHIEVEMENTS = len(ACHIEVEMENTS)


def build_achievement_progress(
    movie_count,
    fresh_release_count,
    language_count,
    genre_count,
    quality_count,
    movie_hours,
):
    """Return a list of the 7 achievements (in ACHIEVEMENTS order), each
    with its live progress for this user/month mixed in:

        {..achievement fields.., "progress": <raw number>,
         "unlocked": bool, "progress_text": "7/10" | "✅ Unlocked"}
    """
    raw_progress = {
        "movie_buff": movie_count,
        "movie_maniac": movie_count,
        "fresh_release_fan": fresh_release_count,
        "explorer": language_count,
        "genre_explorer": genre_count,
        "quality_hunter": quality_count,
        "cinema_addict": round(movie_hours, 1),
    }

    results = []

    for achievement in ACHIEVEMENTS:
        key = achievement["key"]
        target = achievement["target"]
        progress = raw_progress.get(key, 0)
        unlocked = progress >= target

        if unlocked:
            progress_text = "✅ Unlocked"
        elif achievement["unit"] == " hours":
            progress_text = f"{int(round(progress))}/{target} hours"
        else:
            progress_text = f"{int(progress)}/{target}"

        results.append(
            {
                **achievement,
                "progress": progress,
                "unlocked": unlocked,
                "progress_text": progress_text,
            }
        )

    return results
