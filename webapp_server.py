"""
✅ NEW: Telegram Mini App (Web App) server.

Runs as its own process (separate from bot.py) and does two jobs:

1. Serves the static Mini App front-end in /webapp (index.html/style.css/app.js)
   at whatever URL you put in WEBAPP_URL (must be https:// in production -
   Telegram refuses to open Web Apps over plain http, ngrok/Render/Railway
   URLs work fine for testing).

2. Exposes a tiny JSON API the front-end calls to read/manage the watchlist
   that's stored in the same MongoDB collection the bot already writes to:

     GET    /api/watchlist         -> list this user's saved titles
     POST   /api/watchlist/delete  -> remove one title {"imdb_id": "..."}

   Every request must include the Telegram `initData` string (sent as the
   `X-Telegram-Init-Data` header) so we know which user is asking - see
   utils/webapp_auth.py for how that's verified.

Run it with:  python webapp_server.py
"""

import os

from aiohttp import web

from database.watchlist_db import get_watchlist, remove_from_watchlist
from utils.webapp_auth import get_user_id_from_init_data

WEBAPP_DIR = os.path.join(os.path.dirname(__file__), "webapp")


def _get_init_data(request: web.Request) -> str:
    return request.headers.get("X-Telegram-Init-Data", "")


def _unauthorized():
    return web.json_response({"error": "Invalid or missing Telegram auth."}, status=401)


async def api_get_watchlist(request: web.Request):
    user_id = get_user_id_from_init_data(_get_init_data(request))
    if user_id is None:
        return _unauthorized()

    docs = await get_watchlist(user_id)

    items = [
        {
            "imdb_id": doc.get("imdb_id"),
            "title": doc.get("title"),
            "year": doc.get("year"),
            "poster": doc.get("poster"),
            "media_type": doc.get("media_type", "movie"),
        }
        for doc in docs
    ]

    return web.json_response({"items": items})


async def api_delete_watchlist_item(request: web.Request):
    user_id = get_user_id_from_init_data(_get_init_data(request))
    if user_id is None:
        return _unauthorized()

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body."}, status=400)

    imdb_id = body.get("imdb_id")
    if not imdb_id:
        return web.json_response({"error": "imdb_id is required."}, status=400)

    removed = await remove_from_watchlist(user_id, imdb_id)
    return web.json_response({"removed": removed})


@web.middleware
async def cors_middleware(request, handler):
    """Telegram's in-app browser loads the Mini App from a t.me / telegram
    origin, so the API (served from our own domain) needs permissive CORS."""
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])

    app.router.add_get("/api/watchlist", api_get_watchlist)
    app.router.add_post("/api/watchlist/delete", api_delete_watchlist_item)
    app.router.add_route("OPTIONS", "/api/watchlist", lambda r: web.Response())
    app.router.add_route("OPTIONS", "/api/watchlist/delete", lambda r: web.Response())

    # Static Mini App files - keep this route added last so /api/* above wins.
    app.router.add_static("/", WEBAPP_DIR, show_index=False)

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"✅ Watchlist Mini App server starting on port {port} ...")
    web.run_app(create_app(), port=port)
