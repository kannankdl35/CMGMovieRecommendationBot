# Location: plugins/month_watched.py  (NEW FILE)

from pyrogram import Client, filters

from database.month_watched_db import (
    get_month_watched,
    compute_monthly_stats,
    month_key_to_label,
)
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


def build_month_watched_text(docs, month_key=None):
    """Build the numbered This Month Watched listing body for the given
    (already limited/ordered) list of documents.

    The header always shows the current month's name (e.g. "August 2026"),
    derived from `month_key` - since `month_key` itself is always the
    live current-month value (see database/month_watched_db.py's
    current_month_key()), this label updates automatically every calendar
    month with no hardcoding needed."""
    month_label = month_key_to_label(month_key) if month_key else ""
    header = f"📅 **This Month Watched — {month_label}**" if month_label else "📅 **This Month Watched**"

    if not docs:
        return (
            f"{header}\n\n"
            "📭 Nothing marked watched yet.\n\n"
            "Open a title's details page and tap ➕ **Add to This Month "
            "Watched** to start tracking."
        )

    lines = [f"{header}\n"]

    for index, doc in enumerate(docs, start=1):
        title = doc.get("title") or "Unknown"
        year = doc.get("year") or "-"
        media_type = doc.get("media_type", "movie")
        icon = "📺" if media_type == "series" else "🎬"

        lines.append(f"{index}. {icon} {title} ({year})")

    lines.append("\n👇 Tap a number for full details")

    return "\n".join(lines)


def build_monthly_status_text(stats):
    """Build the Monthly Status block (Feature 3) from a stats dict
    produced by database/month_watched_db.py's build_stats_from_docs() /
    compute_monthly_stats(). Shared by the live page below and the
    end-of-month report (services/monthly_report.py).

    The header always shows the month's name (e.g. "August 2026"), derived
    from `stats["month_key"]` - so the live page's header updates
    automatically every calendar month, and the end-of-month report
    (services/monthly_report.py) correctly shows the name of the month
    that just ended rather than the current one."""
    month_label = month_key_to_label(stats.get("month_key"))
    header = f"📊 **Monthly Status — {month_label}**" if month_label else "📊 **Monthly Status**"
    lines = [f"{header}\n"]

    lines.append(f"🎬 **Movies:** {stats['movie_count']}")
    lines.append(f"📺 **Series:** {stats['series_count']}")
    lines.append(
        f"⏱ **Watch Time:** {stats['movie_hours']:.1f}h "
        f"({stats['movie_days']:.1f}d)"
    )
    lines.append(f"🎭 **Top Genre:** {stats['top_genre'] or '-'}")
    lines.append(f"🌐 **Top Language:** {stats['top_language'] or '-'}")
    lines.append(f"🏆 **Achievements:** {stats['unlocked_count']}/7")

    unlocked = [a for a in stats["achievements"] if a["unlocked"]]

    lines.append("\n✅ **Unlocked**")
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

    list_text = build_month_watched_text(docs, month_key=stats["month_key"])
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


async def edit_month_watched_view(client, message, user_id):
    """Edit `message` (the Home menu message the user tapped "🗓️ THIS MONTH
    WATCHED" on) IN PLACE into the current This Month Watched listing +
    Monthly Status, instead of deleting it and sending a brand new message.

    This is what makes tapping "🗓️ THIS MONTH WATCHED" on the Home menu go
    straight into the listing with no delete-then-reappear flash - same
    in-place pattern as plugins/watchlist.py's edit_watchlist_view().

    Also updates the tracked "last This Month Watched message" pointer to
    this same message, so a later refresh (e.g. deleting an item from the
    list, which still uses the delete-then-resend send_month_watched_view()
    above) correctly removes this exact message before sending the fresh
    one.
    """
    text, keyboard = await get_month_watched_view(user_id)

    try:
        await message.edit_text(text=text, reply_markup=keyboard)
        set_last_month_watched_message(user_id, message.chat.id, message.id)
    except Exception:
        # Fallback so This Month Watched still opens even if the edit
        # fails for some reason (e.g. message too old / already deleted).
        await send_month_watched_view(client, message.chat.id, user_id)


@Client.on_message(filters.command(["thismonth", "monthwatched"]))
async def month_watched_command(client, message):
    """Entry point for /thismonth (alias /monthwatched) - same content as
    tapping "🗓️ This Month Watched" on the Home menu."""
    user_id = message.from_user.id

    await send_month_watched_view(client, message.chat.id, user_id)
