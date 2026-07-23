import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ✅ CHANGED: TMDB_API_KEY now also powers "SEARCH - TMDb"
# (services/tmdb.py) - previously it was only used for the "Suggest Me"
# discovery lists, which have been removed.
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# ✅ CHANGED: "SEARCH - IMDb" (services/imdb.py) now uses
# https://mn-api-imdb.vercel.app/ for movie/series search + details.
# No API key is required, so there's nothing to load from the environment
# for it here.

# YouTube Data API (used to fetch official trailers)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "CMGMovieRecommendationBot")
