from pyrogram import Client

from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "CMGMovieRecommendationBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

print("✅ CMG Movie Recommendation Bot Started...")

app.run()
