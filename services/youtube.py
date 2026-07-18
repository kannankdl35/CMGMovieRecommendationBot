import requests

from config import YOUTUBE_API_KEY

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def get_trailer_url(title, year=None):
    """Look up the official trailer on YouTube for a title (Feature 3).
    Returns a direct YouTube watch URL, or None if unavailable/not configured.
    """
    if not YOUTUBE_API_KEY or not title:
        return None

    query = f"{title} {year} official trailer" if year else f"{title} official trailer"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": 1,
    }

    try:
        response = requests.get(SEARCH_URL, params=params, timeout=10)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    items = data.get("items", [])

    if not items:
        return None

    video_id = items[0].get("id", {}).get("videoId")

    if not video_id:
        return None

    return f"https://www.youtube.com/watch?v={video_id}"
