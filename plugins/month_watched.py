# Location: plugins/month_watched.py  (NEW FILE)

from pyrogram import Client, filters

from database.month_watched_db import get_month_watched, compute_monthly_stats
from keyboards.month_watched import month_watched_list_keyboard, achievements_keyboard

# ✅ Tracks the last This Month Watched listing message per user so it can
# be deleted before a new one is sent, avoiding duplicate stacked messages
# whenever the list is refreshed - same pattern as the Watchlist
# (database/user_state.py's set_last_watchlist_message()).
from database.user_state import (
    set_last_month_watched_message,
    get_last_month_watched_message,
)

# The "🗓️ This Month Watched" page works completely INSIDE the Telegram
# chat - no Web App / Mini App page involved.
#
# Tapping "🗓️ This Month Watched" on the Home menu (callback_data
# "month_watched_open", handled in plugins/callback.py) or sending
# /thismonth prints the user's current-month watched titles as a numbered
# text message, this month's stats below it, and matching numbered inline
# buttons underneath (keyboards/month_watched.py). Tapping a number button
# shows that title's full details page - the exact same details view used
# everywhere else (plugins/details.py's send_imdb_details).

WATCHED_DISPLAY_LIMIT = 30  # keeps the text + button grid well within Telegram's limits


def build_month_watched_text(docs):
    """Build the numbered This Month Watched listing body for the given
    (already limited/ordered) list of documents."""
    if not docs:
        return (
            "🗓️ **This Month Watched**\n\n"
            "📭 Nothing marked watched this month yet.\n\n"
            "Open any title's details page and tap ➕ **Add to This Month "
            "Watched** to start tracking."
        )

    lines = ["🗓️ **This Month Watched**\n"]

    for index, doc in enumerate(docs, start=1):
        title = doc.get("title") or "Unknown"
        year = doc.get("year") or "-"
        media_type = doc.get("media_type", "movie")
        icon = "📺" if media_type == "series" else "🎬"

        lines.append(f"{index}. {icon} {title} ({year})")

    lines.append("\nTap a number below to see full details 👇")

    return "\n".join(lines)


def build_monthly_status_text(stats):
    """Build the Monthly Status block (Feature 3) from a stats dict
    produced by database/month_watched_db.py's build_stats_from_docs() /
    compute_monthly_stats(). Shared by the live page below and the
    end-of-month report (services/monthly_report.py)."""
    lines = ["📊 **Monthly Status**\n"]

    lines.append(f"🎬 Movies Watched: {stats['movie_count']}")
    lines.append(f"📺 Series Watched: {stats['series_count']}")
    lines.append(
        f"⏱️ Movie Watch Time: {stats['movie_hours']:.1f} hours "
        f"({stats['movie_days']:.1f} days)"
    )
    lines.append(f"🎭 Top Genre: {stats['top_genre'] or '-'}")
    lines.append(f"🌐 Top Language: {stats['top_language'] or '-'}")
    lines.append(f"🏆 Achievements Unlocked: {stats['unlocked_count']}/7")

    unlocked = [a for a in stats["achievements"] if a["unlocked"]]

    lines.append("\n✅ **Unlocked Achievements**")
    if unlocked:
        for achievement in unlocked:
            lines.append(f"{achievement['icon']} {achievement['name']}")
    else:
        lines.append("None yet")

    return "\n".join(lines)


def build_achievements_text(stats):
    """Build the full "🏆 See the Achievements" page (Feature 4) - every
    achievement with its criteria and this user's current progress."""
    lines = ["🏆 **Achievements**\n"]

    for achievement in stats["achievements"]:
        lines.append(f"{achievement['icon']} **{achievement['name']}** — {achievement['criteria']}")
        lines.append(f"Progress: {achievement['progress_text']}\n")

    return "\n".join(lines).strip()


async def get_month_watched_view(user_id):
    """Return (text, keyboard) for this user's current This Month Watched
    listing + Monthly Status, shared by the "month_watched_open" /
    "mw_achievements_back" callbacks and the /thismonth command."""
    stats = await compute_monthly_stats(user_id)
    docs = stats["docs"][:WATCHED_DISPLAY_LIMIT]

    list_text = build_month_watched_text(docs)
    status_text = build_monthly_status_text(stats)

    text = f"{list_text}\n\n{status_text}"
    keyboard = month_watched_list_keyboard(docs)

    return text, keyboard


async def send_month_watched_view(client, chat_id, user_id):
    """Delete the user's previous This Month Watched listing message (if
    any) and send a fresh one, remembering its message_id for next time -
    same duplicate-avoidance pattern as plugins/watchlist.py's
    send_watchlist_view()."""
    text, keyboard = await get_month_watched_view(user_id)

    previous = get_last_month_watched_message(user_id)
    if previous:
        prev_chat_id, prev_message_id = previous
        try:
            await client.delete_messages(prev_chat_id, prev_message_id)
        except Exception:
            pass

    sent = await client.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    set_last_month_watched_message(user_id, chat_id, sent.id)

    return sent


@Client.on_message(filters.command(["thismonth", "monthwatched"]))
async def month_watched_command(client, message):
    """Entry point for /thismonth (alias /monthwatched) - same content as
    tapping "🗓️ This Month Watched" on the Home menu."""
    user_id = message.from_user.id

    await send_month_watched_view(client, message.chat.id, user_id)
