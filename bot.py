import asyncio

from pyrogram import Client, idle

from config import API_ID, API_HASH, BOT_TOKEN

# ✅ NEW - "This Month Watched" feature: Monthly Reset & Report background
# task (Feature 5) - detects the calendar month rolling over and sends
# every registered user their final status for the month that just ended.
from services.monthly_report import monthly_watched_scheduler

# ✅ NEW - Release Cache Scheduler: proactively re-scrapes "OTT Release
# This Week" and re-fetches "Theatre Release" (all languages) twice a
# day, instead of only refreshing lazily whenever a user happens to open
# those menus after the cache goes stale.
from services.release_scheduler import release_cache_scheduler

# ✅ NEW - Activity Log Channel: notifies LOG_CHANNEL_ID on every bot
# restart and on every brand-new user (the latter is fired from
# plugins/start.py instead).
from services.logger import send_bot_restart_log

app = Client(
    "CMGMovieRecommendationBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)


async def main():
    await app.start()

    print("✅ CMG Movie Recommendation Bot Started...")

    # ✅ NEW - Activity Log Channel: post a #BotRestarted log every time
    # the process (re)starts. See services/logger.py.
    await send_bot_restart_log(app)

    # Runs for the lifetime of the process alongside normal update
    # handling - app.start()/idle()/app.stop() (instead of app.run()) is
    # what lets this background task coexist with Pyrogram's own event
    # loop.
    asyncio.create_task(monthly_watched_scheduler(app))

    # Refreshes "OTT Release This Week" and "Theatre Release" twice a day
    # (see services/release_scheduler.py) so both lists update on a fixed
    # schedule instead of only whenever a user happens to open the menu.
    asyncio.create_task(release_cache_scheduler())

    await idle()

    await app.stop()


if __name__ == "__main__":
    # IMPORTANT: run on the SAME event loop the Client was constructed on
    # (app.loop), not a new one from asyncio.run(). asyncio.run() creates
    # a brand-new loop, which is different from the loop pyrogram bound
    # its internal dispatcher/update-handling tasks to at Client()
    # instantiation time above - running main() on the wrong loop meant
    # incoming Telegram updates were never actually delivered to any
    # handler, even though the client looked "connected" and healthy.
    app.loop.run_until_complete(main())
