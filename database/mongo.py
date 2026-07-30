# Location: database/mongo.py  (REPLACE ENTIRE FILE)

from motor.motor_asyncio import AsyncIOMotorClient

from config import MONGO_URI, DATABASE_NAME

# ✅ Shared MongoDB client/database (Feature 5)
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]

# Collection used to store each user's personal watchlist
watchlist_collection = db["watchlist"]

# ✅ NEW - "This Month Watched" feature
# Each document is one title a user marked watched, tagged with the
# calendar month (month_key, "YYYY-MM") it was added in - see
# database/month_watched_db.py. Keeping past months' documents around
# (instead of deleting them) is what makes the monthly reset "free": a
# new month's queries simply filter to a month_key nothing has been
# added under yet, and the previous month's data is never touched or
# read into the new month's achievements/statistics.
month_watched_collection = db["month_watched"]

# Minimal record of every user who has ever started the bot, so the
# end-of-month report (Feature 5) can message every registered user,
# including ones with all-zero stats for the month.
users_collection = db["users"]

# Tiny single-document collection used to track which calendar month the
# monthly report scheduler last considered "active", so it can detect a
# month rollover exactly once even across bot restarts.
bot_state_collection = db["bot_state"]
