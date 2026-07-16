import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# TMDb API
TMDB_API_KEY = os.getenv("6139cdeb3a5b302d69c5e07c6af3a9cd")

# MongoDB
MONGO_URI = os.getenv("mongodb+srv://movierecbot:cmg@123@cluster0.jprhzud.mongodb.net/?appName=Cluster0")
DATABASE_NAME = os.getenv("DATABASE_NAME", "CMGMovieRecommendationBot")
