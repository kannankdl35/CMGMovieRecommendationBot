import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# ✅ NEW: OMDb API (used for movie/series search + rich details, Feature 1 & 2)
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

# ✅ NEW: YouTube Data API (used to fetch official trailers, Feature 3)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "CMGMovieRecommendationBot")

# ✅ NEW: Telegram Mini App (Web App) - public HTTPS URL where webapp_server.py
# is deployed (serves the /webapp front-end + /api/watchlist endpoints).
# Must be https:// - Telegram will not open a Web App button over plain http.
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
