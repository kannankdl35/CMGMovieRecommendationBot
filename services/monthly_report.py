# Location: services/monthly_report.py  (NEW FILE)

import asyncio

from database.mongo import bot_state_collection
from database.users_db import get_all_user_ids
from database.month_watched_db import current_month_key, compute_monthly_stats
from plugins.month_watched import build_monthly_status_text

# ---------------------------------------------------------------------------
# ✅ NEW - "This Month Watched" feature: Monthly Reset & Report (Feature 5)
#
# How the "reset" itself works: every This Month Watched document is tagged
# with the month_key ("YYYY-MM") it was added in (see
# database/month_watched_db.py). A new calendar month's queries are simply
# scoped to a month_key nothing has been added under yet, so stats and
# achievements start from zero automatically - no deletion, and the
# previous month's data is never read into the new month's numbers.
#
# The only thing that needs an active background process is the REPORT:
# once a month ends, every registered user (database/users_db.py) should
# get a message with their final status for the month that just ended,
# even if every number in it is zero. This module detects that rollover
# and sends it exactly once, tracked in bot_state_collection so a bot
# restart never sends a duplicate.
# ---------------------------------------------------------------------------

CHECK_INTERVAL_SECONDS = 1800  # 30 minutes - frequent enough to catch the
                               # rollover promptly without hammering the DB
STATE_DOC_ID = "monthly_watched_report"
SEND_PACE_SECONDS = 0.05  # gentle pacing between messages in the broadcast


async def _get_active_month():
    doc = await bot_state_collection.find_one({"_id": STATE_DOC_ID})
    return doc.get("active_month") if doc else None


async def _set_active_month(month_key):
    await bot_state_collection.update_one(
        {"_id": STATE_DOC_ID},
        {"$set": {"active_month": month_key}},
        upsert=True,
    )


async def send_final_report_for_month(client, month_key):
    """Send every registered user their final status for `month_key` (the
    month that just ended) - including users whose stats are all zero, per
    the spec. Reuses compute_monthly_stats()/build_monthly_status_text() -
    the exact same numbers the live "This Month Watched" page shows -
    instead of duplicating any stats logic.
    """
    user_ids = await get_all_user_ids()

    for user_id in user_ids:
        try:
            stats = await compute_monthly_stats(user_id, month_key=month_key)
            text = "🎉 **Your Monthly Wrap-Up**\n\n" + build_monthly_status_text(stats)
            await client.send_message(chat_id=user_id, text=text)
        except Exception:
            # A user may have blocked the bot, deleted their Telegram
            # account, etc - skip them and keep the broadcast going rather
            # than letting one bad send stop everyone else's report.
            pass

        await asyncio.sleep(SEND_PACE_SECONDS)


async def monthly_watched_scheduler(client):
    """Background loop (started from bot.py) that detects when the
    calendar month has rolled over and, when it has, sends every
    registered user their final status for the month that just ended,
    then marks the new month as active so it's never reported twice.

    Persisted in bot_state_collection (not just in memory) so this is
    correct even if the bot restarts right around a month boundary.
    """
    active_month = await _get_active_month()

    if active_month is None:
        # First run ever for this bot/database - nothing to report yet,
        # just record the current month as the baseline.
        await _set_active_month(current_month_key())

    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        try:
            active_month = await _get_active_month()
            now_month = current_month_key()

            if active_month and now_month != active_month:
                await send_final_report_for_month(client, active_month)
                await _set_active_month(now_month)
        except Exception:
            # Never let a scheduler hiccup take down the whole bot process.
            continue
