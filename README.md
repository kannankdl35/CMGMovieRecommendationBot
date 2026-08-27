# 🎬 CMG Movie Recommendation Bot

A feature-rich Telegram bot for discovering, tracking, and getting recommendations for movies and TV series — built with [Pyrogram](https://docs.pyrogram.org/), backed by MongoDB, and powered by the TMDb and IMDb APIs.

Search titles inline, browse trending and upcoming releases by language, get a random 7★+ pick, keep a personal watchlist, track what you watch every month with unlockable achievements, and customize exactly how results are displayed — all without leaving the Telegram chat.

---

## ✨ Features

### 🔍 Search & Discovery
- **Search - TMDb / Search - IMDb** — type a title via Telegram inline mode (`@YourBot tmdb `/`imdb `), tap a result, and get a full details card: poster, year, runtime, genres, rating, director, writers, cast, and plot.
- **Download Posters** — same inline search flow, but sends up to 10 full-resolution posters for a title as an album, no caption or buttons.
- **Trending** — Today or This Week, sourced from TMDb's trending endpoints.
- **Upcoming** — Theatre Release or OTT Release This Week, filterable by Malayalam, Tamil, Telugu, Kannada, Hindi, or English. Regional OTT data is scraped from `ottreleasesthisweek.com`; English OTT and all theatre data come from TMDb.
- **Random Pick** — choose a language (Malayalam, Tamil, Hindi, Kannada, Telugu, English, Korean, or Others) and get a random movie recommendation, always rated 7★+ (with a minimum vote-count floor that scales by language).

### 📋 Personal Tracking
- **Watchlist** — save any title from its details page and revisit it anytime via `/watchlist` or the Home menu, up to 30 shown at once.
- **This Month Watched** — mark movies/series watched from their details page; view a numbered list, a Monthly Status summary (movie/series counts, watch time, top genre, top language), and progress toward 7 achievements:

  | Achievement | Criteria |
  |---|---|
  | 🍿 Movie Buff | Watch 10 movies |
  | 🎞️ Movie Maniac | Watch 20 movies |
  | 🆕 Fresh Release Fan | Watch 5 movies released this year |
  | 🌍 Explorer | Watch movies in 5 different languages |
  | 🎭 Genre Explorer | Watch movies from 7 different genres |
  | ⭐ Quality Hunter | Watch 5 movies rated 7.0+ |
  | 🎬 Cinema Addict | Watch 75 hours of movies |

  A background scheduler detects each calendar month rollover and DMs every registered user their final status for the month that just ended (even if it's all zeros), then resets automatically — no data is deleted, each entry is simply tagged with the month it was added in.

### ⚙️ Customization
- **Settings** — per-user toggles for which detail fields (poster, title, year, runtime, genres, rating, cast, plot, etc.) appear on IMDb/TMDb result cards, independently for each source.
- **Custom Caption** — replace the default caption entirely with your own template using `#TAG` placeholders (`#TITLE`, `#YEAR`, `#RATING`, `#GENRES`, `#CAST`, `#PLOT`, and more), mixed with your own text — perfect for branding results with a channel name or username. Manage with `/show_custom_caption` and `/delete_custom_caption`.

### 🛠 Admin Tools
- **`/stats`** — total users, new users today, total searches, and MongoDB storage used/free. Open to everyone unless `ADMIN_IDS` is set.
- **`/broadcast`** — reply to any message (text, photo, video, audio, document, link) with this command to copy it to every registered user, with a live-updating progress message (Total / Success / Blocked / Failed). Always admin-only.
- **Activity Log Channel** — posts `#NewUser` on every first-time `/start` and `#BotRestarted` on every process restart to a private channel, if configured.

### ℹ️ Info
- **About** — bot name, version, framework, database, hosting, developer, and channel links.
- **Help** (`/help` or the ❓ button) — a full walkthrough of every feature above.

---

## 🤖 Commands

| Command | Description |
|---|---|
| `/start` | Registers the user and opens the Home menu |
| `/help` | Shows the full feature guide |
| `/watchlist` | Opens your saved watchlist |
| `/thismonth`, `/monthwatched` | Opens this month's watched list, stats, and achievements |
| `/show_custom_caption` | Shows your saved custom caption templates |
| `/delete_custom_caption` | Removes a saved custom caption template |
| `/stats` | Bot usage stats (public by default, or admin-only if `ADMIN_IDS` is set) |
| `/broadcast` | Reply to a message to broadcast it to all users (admin-only) |

Most other features (Search, Trending, Upcoming, Random, Settings, About) are accessed via the inline buttons on the Home menu rather than slash commands.

---

## 🧱 Tech Stack

- **Language:** Python 3
- **Telegram framework:** [Pyrogram](https://docs.pyrogram.org/) (+ TgCrypto for faster crypto)
- **Database:** MongoDB, accessed asynchronously via [Motor](https://motor.readthedocs.io/)
- **Movie/TV data:** [TMDb API](https://www.themoviedb.org/documentation/api), [mn-api-imdb](https://imdb.iamidiotareyoutoo.com/docs/index.html) (no key required)
- **Web scraping:** BeautifulSoup4 (regional OTT release calendar)
- **Config:** python-dotenv

---

## 📁 Project Structure

```
CMGMovieRecommendationBot/
├── bot.py                      # Entry point — starts the client and background schedulers
├── config.py                   # Loads and validates all environment variables
├── requirements.txt
├── Procfile                    # worker: python bot.py
│
├── about/
│   └── about_info.py           # Editable text for the About & Help pages
│
├── database/
│   ├── mongo.py                # Shared Motor client + collection references
│   ├── users_db.py             # User registration
│   ├── watchlist_db.py         # Watchlist storage
│   ├── month_watched_db.py     # "This Month Watched" storage + stats
│   ├── settings_db.py          # Per-user field-toggle & custom caption settings
│   ├── stats_db.py             # Aggregates for /stats
│   └── user_state.py           # Ephemeral per-user UI state (last message ids, awaiting input, etc.)
│
├── keyboards/                  # Inline keyboard builders for every menu
│
├── plugins/                    # Pyrogram message/callback handlers (the bot's "controllers")
│   ├── start.py, help.py, watchlist.py, month_watched.py
│   ├── custom_caption.py, stats.py, broadcast.py
│   ├── inline.py               # Inline search query handler
│   ├── callback.py             # Central handler for nearly every inline button
│   ├── details.py              # Builds/sends title details pages
│   └── posters.py              # Sends the poster album
│
├── services/                   # External API clients & background jobs
│   ├── tmdb.py, imdb.py        # Search/details backends
│   ├── theatre_releases.py     # TMDb theatrical release listings
│   ├── ott_releases.py         # Scraped + TMDb OTT release listings
│   ├── release_scheduler.py    # Refreshes release caches twice daily
│   ├── monthly_report.py       # Detects month rollover, sends end-of-month reports
│   └── logger.py               # Activity log channel notifications
│
└── utils/
    ├── formatter.py             # Builds default & custom captions
    └── achievements.py          # Achievement definitions & progress calculation
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.9+
- A Telegram **API ID / API Hash** from [my.telegram.org](https://my.telegram.org)
- A **Bot Token** from [@BotFather](https://t.me/BotFather)
- A **TMDb API key** from [themoviedb.org](https://www.themoviedb.org/settings/api)
- A **MongoDB** connection string (e.g. a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster)

### 2. Clone & install dependencies
```bash
git clone <your-repo-url>
cd CMGMovieRecommendationBot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install beautifulsoup4   # required by services/ott_releases.py — see Known Issues below
```

### 3. Configure environment variables
Copy the sample file and fill in your own values:
```bash
cp .env.sample .env
```

| Variable | Required | Description |
|---|---|---|
| `API_ID` | ✅ | Telegram API ID |
| `API_HASH` | ✅ | Telegram API Hash |
| `BOT_TOKEN` | ✅ | Bot token from BotFather |
| `TMDB_API_KEY` | ✅ | Powers Search - TMDb, Trending, Upcoming, Random, and Posters |
| `MONGO_URI` | ✅ | MongoDB connection string |
| `DATABASE_NAME` | – | Defaults to `CMGMovieRecommendationBot` |
| `LOG_CHANNEL_ID` | – | Chat ID of a channel the bot admins, for `#NewUser`/`#BotRestarted` logs. Leave unset to disable |
| `ADMIN_IDS` | – | Comma-separated Telegram user IDs allowed to run `/stats` and `/broadcast`. Leave `/stats`'s check unset to make it public; `/broadcast` always requires this to be set |
| `MONGO_STORAGE_LIMIT_MB` | – | Your Atlas storage quota, for the `/stats` "Free Storage" figure. Defaults to `512` (Atlas free tier) |

> ℹ️ IMDb search needs no API key (uses a free public endpoint), and the old `YOUTUBE_API_KEY` entry in `.env.sample` is a leftover from a removed Trailer feature — it's safe to delete.

### 4. Run the bot
```bash
python bot.py
```
On success you'll see `✅ CMG Movie Recommendation Bot Started...` in the console.

---

## ☁️ Deployment

A `Procfile` (`worker: python bot.py`) is included for any platform that reads one (Heroku-style worker dynos, Railway, etc.). The bot itself has been run on Oracle Cloud, but it isn't tied to any specific host — anywhere that can keep a long-running Python process alive with your `.env` variables set will work.

The bot runs two background tasks alongside normal message handling: a **monthly report scheduler** (checks every 30 minutes for a new calendar month) and a **release cache scheduler** (refreshes Theatre/OTT release data twice a day).

---

## ⚠️ Known Issues / Notes

- **Missing dependency:** `services/ott_releases.py` imports `beautifulsoup4`, but it isn't listed in `requirements.txt`. Install it manually (`pip install beautifulsoup4`) or add `beautifulsoup4` to `requirements.txt` yourself.
- **IMDb by-id lookups** can occasionally return mismatched or incomplete data for TV series (a known limitation of the underlying free API) — the bot retries automatically and falls back to trusted cached fields rather than showing a wrong title.
- **Theatre release scraping** via TMDb's discover filter hasn't been separately load-tested; treat early runs as a smoke test.

## 🔒 Security Note

Never commit a real `.env` file — `.gitignore` already excludes it, but make sure any zip/export of this project you share doesn't include it either, since it contains live secrets (bot token, API keys, database credentials). If a real `.env` has ever been shared or committed, rotate every credential in it (BotFather token, TMDb key, MongoDB user password) immediately.

---

## 👤 Credits

- **Developer:** [Deepak](https://t.me/CMG_4dmin)
- **Channel:** [Cinemagram](https://t.me/cinemagram_links)
- **Bug reports:** message [@CMG_4dmin](https://t.me/CMG_4dmin) on Telegram
