import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# ✅ CHANGED: OMDb API replaced with the key-less IMDb API
# (https://imdb.iamidiotareyoutoo.com/docs/index.html, see
# services/imdb.py) for movie/series search + rich details (Feature 1 & 2).
# No API key is required, so there's nothing to load from the environment
# here anymore.

# ✅ NEW: YouTube Data API (used to fetch official trailers, Feature 3)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "CMGMovieRecommendationBot")

# ✅ REMOVED: WEBAPP_URL - the Telegram Web App / Mini App has been removed.
# The watchlist now renders entirely inside the Telegram chat
# (see plugins/watchlist.py), so no public HTTPS URL is needed anymore.
