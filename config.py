import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# TMDB_API_KEY powers "SEARCH - TMDb" (services/tmdb.py).
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# "SEARCH - IMDb" (services/imdb.py) uses https://mn-api-imdb.vercel.app/
# for movie/series search + details. No API key required.

# ✅ REMOVED: YOUTUBE_API_KEY - the Trailer feature has been removed
# entirely, so this is no longer read. Safe to delete YOUTUBE_API_KEY from
# your .env too if nothing else uses it.

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "CMGMovieRecommendationBot")

# ✅ NEW - Activity Log Channel
# Private chat/channel the bot posts #NewUser and #BotRestarted logs to
# (see services/logger.py). Make the bot an admin there. Left unset (None)
# is safe - logging just silently no-ops instead of erroring.
_log_channel_id = os.getenv("LOG_CHANNEL_ID")
LOG_CHANNEL_ID = int(_log_channel_id) if _log_channel_id else None

# ✅ NEW - /stats command
# Comma-separated Telegram user ids allowed to run /stats, e.g.
#   ADMIN_IDS=123456789,987654321
# Leave unset/empty in .env to allow ANY user to run /stats - only do that
# if you're fine with total-user/storage/search numbers being public.
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {
    int(uid.strip()) for uid in _admin_ids_raw.split(",") if uid.strip()
}

# ✅ NEW - /stats command: total MongoDB storage quota in MB, used to
# compute "Free Storage" as (limit - used). 512 is MongoDB Atlas' free
# tier (M0) cap - override in .env if you're on a paid tier.
MONGO_STORAGE_LIMIT_MB = float(os.getenv("MONGO_STORAGE_LIMIT_MB", "512"))
