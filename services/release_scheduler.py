# Location: services/release_scheduler.py  (NEW FILE)

import asyncio

from services.ott_releases import get_cached_ott_releases
from services.theatre_releases import get_cached_theatre_releases, LANGUAGE_CODES

# ---------------------------------------------------------------------------
# 🔄 Release Cache Scheduler
#
# Both services/ott_releases.py ("OTT Release This Week") and
# services/theatre_releases.py ("Theatre Release") cache their data and
# only refresh it LAZILY - i.e. the next time some user happens to open
# that menu after the cache has gone stale. That's fine for keeping
# per-request cost low, but it means the list only updates "whenever
# someone next asks", not on a real schedule - if nobody opens the menu
# right when it goes stale, everyone keeps seeing the previous list.
#
# This module fixes that by actively pushing a refresh on a fixed
# schedule (twice a day), independent of user traffic, so both sections
# are always backed by a fresh scrape/fetch rather than whatever the
# last visitor happened to trigger.
#
# Started as a background asyncio task from bot.py, the same way
# services/monthly_report.py's monthly_watched_scheduler() is - runs for
# the lifetime of the process alongside normal update handling.
# ---------------------------------------------------------------------------

CHECK_INTERVAL_SECONDS = 12 * 60 * 60  # twice a day


async def _refresh_ott():
    """OTT Release This Week covers every regional language plus English
    in a single call - get_cached_ott_releases() batches all 6 languages
    internally, so one forced refresh here is enough."""
    try:
        await asyncio.to_thread(get_cached_ott_releases, True)
    except Exception:
        # A scrape failure here should never crash the scheduler loop -
        # get_cached_ott_releases() already falls back to serving the
        # last good cache on failure, so just try again next cycle.
        pass


async def _refresh_theatre():
    """Theatre Release is cached per-language (one TMDb request each), so
    refresh every language separately - a failure on one language must
    not stop the others from refreshing."""
    for lang in LANGUAGE_CODES:
        try:
            await asyncio.to_thread(get_cached_theatre_releases, lang, True)
        except Exception:
            pass


async def refresh_all_release_caches():
    """One full refresh pass - both OTT and Theatre, every language.
    Exposed on its own (not just inside the loop below) so it can also
    be triggered manually, e.g. from an admin command, without waiting
    for the next scheduled tick."""
    await _refresh_ott()
    await _refresh_theatre()


async def release_cache_scheduler():
    """Background loop (started from bot.py). Refreshes both release
    caches immediately on startup - so a freshly deployed/restarted bot
    never serves a stale in-memory cache while waiting for the first
    tick - then repeats every CHECK_INTERVAL_SECONDS (12h), giving two
    refreshes a day for as long as the process stays up.
    """
    while True:
        try:
            await refresh_all_release_caches()
        except Exception:
            # Never let a scheduler hiccup take down the whole bot process.
            pass

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
