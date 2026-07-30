# Location: bot.py  (REPLACE ENTIRE FILE)

import asyncio

from pyrogram import Client, idle

from config import API_ID, API_HASH, BOT_TOKEN

# ✅ NEW - "This Month Watched" feature: Monthly Reset & Report background
# task (Feature 5) - detects the calendar month rolling over and sends
# every registered user their final status for the month that just ended.
from services.monthly_report import monthly_watched_scheduler

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

    # Runs for the lifetime of the process alongside normal update
    # handling - app.start()/idle()/app.stop() (instead of app.run()) is
    # what lets this background task coexist with Pyrogram's own event
    # loop.
    asyncio.create_task(monthly_watched_scheduler(app))

    await idle()

    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
