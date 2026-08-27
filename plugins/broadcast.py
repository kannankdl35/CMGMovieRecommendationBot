# # Location: plugins/broadcast.py  (NEW FILE)

import asyncio
import time

from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid

from config import ADMIN_IDS
from database.users_db import get_all_user_ids

print("✅ BROADCAST PLUGIN LOADED")

# ---------------------------------------------------------------------------
# ✅ NEW - /broadcast command
#
# Workflow (admin-only, gated by config.ADMIN_IDS - see below):
#   1. Admin sends the message they want broadcast (text/photo/video/
#      audio/document/link - any message type) to the bot.
#   2. Admin replies to that message with /broadcast.
#   3. The bot copies that exact message (client-side, via Message.copy())
#      to every registered user (database/users_db.py:get_all_user_ids()).
#      copy() re-sends the message's own content as a brand-new message
#      from the bot - no "Forwarded from" tag - and works for every
#      message type Telegram supports, so text/audio/image/link/video all
#      just work without any special-casing here.
#   4. A single status message is sent once broadcasting starts, then
#      edited in place as it progresses (throttled - see EDIT_EVERY /
#      EDIT_MIN_INTERVAL below - editing on literally every single user
#      would run straight into Telegram's edit-rate limits), so the admin
#      watches Total/Completed/Success/Blocked/Deleted update live instead
#      of only seeing a result once everything is done.
#   5. On completion, that same message is edited one final time into the
#      "Broadcast Completed" summary with the total time taken.
#
# Unlike /stats (plugins/stats.py), which is open to everyone when
# ADMIN_IDS is left empty, /broadcast is ALWAYS restricted - an unset
# ADMIN_IDS means nobody can broadcast, since messaging every registered
# user is far higher-stakes than reading a stats number.
# ---------------------------------------------------------------------------

EDIT_EVERY = 20            # also edit at least every N processed users
EDIT_MIN_INTERVAL = 3.0    # ...and never more than once every N seconds
SEND_PACE_SECONDS = 0.05   # small delay between sends, to stay well under
                           # Telegram's rate limits for a bot messaging
                           # many different users back-to-back
MAX_FLOOD_RETRIES = 5      # how many times to wait-out a FloodWait on the
                           # same user before giving up on them


def _format_elapsed(seconds: float) -> str:
    """Format a duration as H:MM:SS, e.g. 7325.0 -> '2:02:05'."""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def _status_text(total, completed, success, blocked, deleted, *, done=False, elapsed=None):
    header = "✅ **--Broadcast Complete--**" if done else "📢 **--Broadcasting…--**"
    lines = [header]

    if done and elapsed is not None:
        lines.append(f"Finished in {_format_elapsed(elapsed)}")

    lines.append("")
    lines.append(f"👥 **Total:** {total}")
    lines.append(f"⏳ **Progress:** {completed} / {total}")
    lines.append(f"✅ **Success:** {success}")
    lines.append(f"🚫 **Blocked:** {blocked}")
    lines.append(f"❌ **Failed:** {deleted}")

    return "\n".join(lines)


async def _deliver(target, user_id):
    """Copy `target` to `user_id`. Returns 'success', 'blocked', or
    'deleted'. A FloodWait just means Telegram wants us to slow down (not
    that delivery failed), so it's waited out and retried, up to
    MAX_FLOOD_RETRIES times, rather than counted as a failure.
    """
    for _ in range(MAX_FLOOD_RETRIES):
        try:
            await target.copy(chat_id=user_id)
            return "success"
        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue
        except UserIsBlocked:
            return "blocked"
        except (InputUserDeactivated, PeerIdInvalid):
            # Account deactivated/deleted, or the bot has no valid peer
            # for this id (e.g. the user deleted their Telegram account).
            return "deleted"
        except Exception as e:
            # Any other delivery failure - don't let one bad user stall
            # the whole broadcast.
            print(f"⚠️ Broadcast delivery failed for {user_id}: {type(e).__name__}: {e}")
            return "deleted"

    # Kept hitting FloodWait past the retry budget - move on.
    return "deleted"


@Client.on_message(filters.command("broadcast"))
async def broadcast_command(client, message):
    """/broadcast - reply to any message with this command to send that
    exact message (text, photo, video, audio, document, or a link) to
    every registered user, with a live-updating progress message.

    Admin-only: requires config.ADMIN_IDS to be set in .env AND the
    caller's id to be in it. Empty/unset ADMIN_IDS blocks everyone,
    unlike /stats.
    """
    user = message.from_user

    if not user or not ADMIN_IDS or user.id not in ADMIN_IDS:
        await message.reply_text("❌ You're not authorized to use this command.")
        return

    target = message.reply_to_message
    if not target:
        await message.reply_text(
            "⚠️ Reply to the message you want to broadcast with /broadcast.\n\n"
            "Send the message first — text, photo, video, audio, document, "
            "or a link — then reply to it with /broadcast."
        )
        return

    try:
        user_ids = await get_all_user_ids()
    except Exception as e:
        print("⚠️ /broadcast failed to load user list (continuing anyway)")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        await message.reply_text("⚠️ Couldn't load the user list right now. Please try again.")
        return

    total = len(user_ids)
    if total == 0:
        await message.reply_text("⚠️ There are no registered users to broadcast to yet.")
        return

    status_message = await message.reply_text(
        _status_text(total, 0, 0, 0, 0),
        disable_web_page_preview=True,
    )

    completed = success = blocked = deleted = 0
    start_time = time.monotonic()
    last_edit_time = start_time

    for user_id in user_ids:
        outcome = await _deliver(target, user_id)

        if outcome == "success":
            success += 1
        elif outcome == "blocked":
            blocked += 1
        else:
            deleted += 1

        completed += 1

        # Throttled live update: edit at least every EDIT_EVERY users
        # processed, but never more often than every EDIT_MIN_INTERVAL
        # seconds - keeps the progress message current without tripping
        # Telegram's rate limit on message edits.
        now = time.monotonic()
        if (
            completed == total
            or completed % EDIT_EVERY == 0
            or (now - last_edit_time) >= EDIT_MIN_INTERVAL
        ):
            try:
                await status_message.edit_text(
                    _status_text(total, completed, success, blocked, deleted),
                    disable_web_page_preview=True,
                )
                last_edit_time = now
            except FloodWait as e:
                await asyncio.sleep(e.value)
                last_edit_time = time.monotonic()
            except Exception:
                # A failed progress-message edit shouldn't stop the
                # broadcast itself - just try again on the next update.
                pass

        await asyncio.sleep(SEND_PACE_SECONDS)

    elapsed = time.monotonic() - start_time
    final_text = _status_text(
        total, completed, success, blocked, deleted, done=True, elapsed=elapsed
    )

    try:
        await status_message.edit_text(final_text, disable_web_page_preview=True)
    except Exception:
        await message.reply_text(final_text)

