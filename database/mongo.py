from motor.motor_asyncio import AsyncIOMotorClient

from config import MONGO_URI, DATABASE_NAME

# ✅ Shared MongoDB client/database (Feature 5)
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]

# Collection used to store each user's personal watchlist
watchlist_collection = db["watchlist"]
