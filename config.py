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
