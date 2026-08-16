# Location: about/about_info.py  (REPLACE ENTIRE FILE)
#
# ✅ NEW - ℹ️ About feature: every value shown on the "ℹ️ About" page lives
# in this file/folder on its own, so it can be edited any time without
# touching keyboards/about.py (the buttons shown under the text) or
# plugins/callback.py (the "about_open" handler that renders this text -
# see keyboards/home.py for the "ℹ️ About" button that opens it).
#
# Just edit the values below and restart the bot - nothing else needs to
# change.

BOT_NAME = "CMG Movie Info Bot"

DESCRIPTION = (
    "Search any Movie or TV Series and get full details - poster, rating, "
    "cast, plot, and more - powered by IMDb and TMDb."
)

VERSION = "1.0.0"

# Shown as plain text - update this string by hand whenever you ship a
# change.
LAST_UPDATE = "10 August 2026"

PROGRAMMING_LANGUAGE = "Python"

# NOTE: your reference image said "Program" here - this bot is built on
# the Pyrogram framework (see bot.py's `from pyrogram import Client`), so
# this is set to "Pyrogram". Change it if you meant something else.
FRAMEWORK = "Pyrogram"

DATABASE = "MongoDB"

# Developer/Admin - shown as "Deepak (@CMG_4dmin)" with the username
# linked to https://t.me/<DEVELOPER_USERNAME>.
DEVELOPER_NAME = "Deepak"
DEVELOPER_USERNAME = "CMG_4dmin"

# Channel - shown as "Cinemagram (@cinemagram_links)". Telegram
# auto-links a bare "@username" mention in message text on its own, so no
# manual URL is needed here.
CHANNEL_NAME = "Cinemagram"
CHANNEL_USERNAME = "cinemagram_links"

# Hosting - shown as "Oracle", linked to HOSTING_URL below. Point this at
# whichever Oracle Cloud page you'd like users to land on.
HOSTING_NAME = "Oracle"
HOSTING_URL = "https://www.oracle.com/cloud/"

# Source - shown as a "Click Here" link.
SOURCE_URL = "https://t.me/Thekkott_Nokki_Irunno/2"

# 🐞 Report Issues/Bugs button (below the text, see keyboards/about.py)
# opens a chat with this username.
REPORT_USERNAME = "CMG_4dmin"


def build_about_text():
    """Builds the "ℹ️ About" page text shown by plugins/callback.py's
    "about_open" handler, entirely from the values above.
    """

    developer_link = f"[@{DEVELOPER_USERNAME}](https://t.me/{DEVELOPER_USERNAME})"
    hosting_link = f"[{HOSTING_NAME}]({HOSTING_URL})"
    source_link = f"[Click Here]({SOURCE_URL})"

    return (
        f"ℹ️ **{BOT_NAME}**\n\n"
        f"{DESCRIPTION}\n\n"
        f"🏷 **Version:** {VERSION}\n"
        f"🗓 **Last Update:** {LAST_UPDATE}\n"
        f"👤 **Developer:** {DEVELOPER_NAME} ({developer_link})\n"
        f"📣 **Channel:** {CHANNEL_NAME} (@{CHANNEL_USERNAME})\n\n"
        f"🐍 **Built with:** {PROGRAMMING_LANGUAGE} · {FRAMEWORK}\n"
        f"🗄 **Database:** {DATABASE}\n"
        f"☁️ **Hosting:** {hosting_link}\n"
        f"💻 **Source:** {source_link}"
    )


# ✅ NEW - ❓ Help feature: opened from the "❓ Help" button on the "ℹ️ About"
# page (keyboards/about.py's help_keyboard(), wired up by the "help_open"
# callback in plugins/callback.py). Walks through every feature on the
# Home menu (keyboards/home.py) in one place, for a user who isn't sure
# what the bot can do.
def build_help_text():
    """Builds the "❓ Help" page text - a full feature guide - shown by
    plugins/callback.py's "help_open" handler.
    """

    return (
        "❓ **Help — What This Bot Can Do**\n\n"
        "🔍 **Search**\n"
        "Tap 🔍 Search - IMDb or 🔍 Search - TMDb, type a title, then tap "
        "a result for full details — poster, rating, cast, plot & more.\n\n"
        "⬇️ **Download Posters**\n"
        "Same search, but sends every poster on file for that title at "
        "full resolution.\n\n"
        "🔥 **Trending**\n"
        "See what's trending on TMDb today or this week.\n\n"
        "🎬 **Upcoming**\n"
        "Browse upcoming theatre releases and this week's OTT releases, "
        "by language.\n\n"
        "🎲 **Random Pick**\n"
        "Pick a language and get a random movie recommendation, always "
        "rated 7★+.\n\n"
        "📋 **Watchlist**\n"
        "Save any title to watch later, right from its details page.\n\n"
        "📅 **This Month Watched**\n"
        "Track what you've watched this month, unlock achievements, and "
        "get a wrap-up report when the month ends.\n\n"
        "⚙️ **Settings**\n"
        "Choose which fields (rating, cast, plot, etc.) show in your "
        "results, or set your own custom caption template.\n\n"
        "ℹ️ **About**\n"
        "Bot info, version, and how to reach the developer.\n\n"
        "Still stuck? Tap 🐞 Report Issues/Bugs on the About page."
    )
