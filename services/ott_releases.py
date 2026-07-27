import re

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Scrapes https://ottreleasesthisweek.com/ for the weekly Indian
# regional-language OTT release list (Malayalam, Tamil, Telugu, Kannada,
# Hindi) - no API involved. Confirmed live (see chat) to have clean,
# consistently-structured per-title blocks:
#
#   ### <Movie Title>
#   - Release Date: <date>
#   - OTT Platform: <platform(s)>
#   - Language: <language list, e.g. "Tamil (Original), Telugu, ...">
#   - Genre: <genre>
#
# Meant to be called ONCE A DAY by a scheduled job and cached - never per
# user request - so this has no rate-limit/quota concern at all, unlike
# every commercial API we tested (Watchmode, TMDb digital-release data,
# JustWatch). The tradeoff: no SLA, and it breaks if the site changes its
# layout or goes offline - get_weekly_regional_releases() below returns an
# empty dict rather than raising, so a caller can show "no data today"
# instead of crashing.
# ---------------------------------------------------------------------------

HOMEPAGE_URL = "https://ottreleasesthisweek.com/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; personal Telegram bot; "
        "fetches once daily for a cached release list)"
    )
}

TARGET_LANGUAGES = ["malayalam", "tamil", "telugu", "kannada", "hindi"]

FIELD_PATTERN = re.compile(
    r"Release Date:\s*(?P<date>[^\n]+?)\s*\n*"
    r"OTT Platform:\s*(?P<platform>[^\n]+?)\s*\n*"
    r"Language:\s*(?P<language>[^\n]+?)\s*\n*"
    r"Genre:\s*(?P<genre>[^\n]+)",
    re.IGNORECASE,
)


def _find_latest_india_post_url():
    """The homepage lists posts newest-first, mixing general "India"
    roundups (all regional languages together) with Telugu-only and
    English/Hollywood-only posts. The general roundup's slug reliably
    contains "india" - this returns the first (newest) matching link.
    """
    response = requests.get(HOMEPAGE_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href in seen:
            continue
        seen.add(href)

        if "ottreleasesthisweek.com" not in href:
            continue
        if "/category/" in href or "/tag/" in href:
            continue

        slug = href.rstrip("/").rsplit("/", 1)[-1].lower()
        if "india" in slug:
            return href

    return None


def _extract_release_blocks(html):
    """Walk headings in document order; a heading counts as a movie title
    only if the text between it and the next heading contains all four
    expected fields - filters out section headers, "Also read" links, and
    nav without depending on any specific CSS class.
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []

    for heading in soup.find_all(["h2", "h3", "h4"]):
        title = heading.get_text(strip=True)
        if not title:
            continue

        block_parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ("h2", "h3", "h4"):
                break
            block_parts.append(sibling.get_text("\n", strip=True))
        block_text = "\n".join(block_parts)

        match = FIELD_PATTERN.search(block_text)
        if not match:
            continue

        entries.append(
            {
                "title": title,
                "release_date": match.group("date").strip(),
                "platform": match.group("platform").strip(),
                "language": match.group("language").strip(),
                "genre": match.group("genre").strip(),
            }
        )

    return entries


def get_weekly_regional_releases():
    """Fetch this week's regional-language OTT releases.

    Returns a dict keyed by language -> list of release entries, e.g.
    {"malayalam": [...], "tamil": [...], ...}. A pan-Indian release
    tagged with multiple languages appears in every matching language's
    list. Returns {} on any failure - see module notes above.
    """
    try:
        post_url = _find_latest_india_post_url()
        if not post_url:
            return {}

        response = requests.get(post_url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        entries = _extract_release_blocks(response.text)
    except Exception:
        return {}

    by_language = {lang: [] for lang in TARGET_LANGUAGES}

    for entry in entries:
        language_field = entry["language"].lower()
        for lang in TARGET_LANGUAGES:
            if lang in language_field:
                by_language[lang].append(entry)

    return by_language
