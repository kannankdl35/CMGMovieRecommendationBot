from pyrogram import Client

from config import API_ID, API_HASH, BOT_TOKEN

# Import Plugins
import plugins.start
import plugins.callback
import plugins.movie
import plugins.series
import plugins.details

app = Client(
    "CMGMovieRecommendationBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

print("✅ CMG Movie Recommendation Bot Started...")

app.run()
