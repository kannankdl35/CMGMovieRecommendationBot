# # Location: plugins/custom_caption.py  (NEW FILE)

from pyrogram import Client, filters, ContinuePropagation

from database.settings_db import (
    get_custom_caption,
    set_custom_caption,
    delete_custom_caption,
)
from database.user_state import (
    get_awaiting_custom_caption,
    clear_awaiting_custom_caption,
)
from keyboards.custom_caption import delete_custom_caption_keyboard
from utils.formatter import caption_tags_for

print("✅ CUSTOM CAPTION PLUGIN LOADED")

# ---------------------------------------------------------------------------
# ✅ NEW - ✏️ Custom Caption feature
#
# Lets each user fully replace the normal field-by-field IMDb/TMDb
# caption (utils/formatter.py's format_imdb_details()) with their own
# template, per source - opened via "✏️ Custom Caption" under
# 🎥 IMDb Settings / 📽 TMDb Settings (keyboards/settings.py, wired up in
# plugins/callback.py).
#
# Flow:
#   1. Tapping "✏️ Custom Caption" (callback_data
#      "custom_caption_imdb_open" / "custom_caption_tmdb_open", handled
#      in plugins/callback.py) shows custom_caption_page_text() below -
#      the tags available for that source, an example, and this user's
#      current template (if any) - and marks them as awaiting a template
#      for that source (database/user_state.py's
#      set_awaiting_custom_caption()).
#   2. The very next plain-text message they send (private chat with the
#      bot) is caught by receive_custom_caption() below and saved as
#      their new template for that source
#      (database/settings_db.py's set_custom_caption()) - this is what
#      lets them mix in their own text (channel name, username, etc.)
#      alongside the #TAG placeholders.
#   3. /show_custom_caption re-shows whatever is currently saved for
#      both sources at any time.
#   4. /delete_custom_caption removes a saved template (asks which
#      source, if both are saved) and reverts that source back to the
#      normal caption.
#
# Tapping ANY other button cancels "awaiting" mode without saving
# anything (see the top of plugins/callback.py's callback_handler()).
#
# A saved custom caption completely replaces the caption TEXT for that
# source - the per-field ✅/❌ toggles (also under IMDb/TMDb Settings)
# have no effect on it. The Poster toggle is the one exception: it still
# decides whether the result is sent as a photo attachment at all (see
# plugins/details.py's _resolve_display()/_build_caption()), independent
# of whatever caption text ends up under it.
# ---------------------------------------------------------------------------

SOURCE_NAMES = {"imdb": "IMDb", "tmdb": "TMDb"}


def custom_caption_page_text(source, current):
    """Text for the "✏️ Custom Caption" page itself (opened from IMDb/
    TMDb Settings) - the tags this source supports, an example, and
    whatever template is currently saved for it (or "Default" if none).
    """
    name = SOURCE_NAMES[source]

    current_block = (
        f"```\n{current}\n```" if current else "❌ **--Default--** — __no custom caption saved.__"
    )

    tags_line = " ".join(f"#{tag}" for tag in caption_tags_for(source))

    return (
        f"📝 **--{name} Custom Caption--**\n\n"
        f"Create your own caption template for every {name} result. Add "
        "your text, tags, and even a channel name or username.\n\n"
        "**--Available Tags--**\n"
        f"{tags_line}\n\n"
        "**--Example--**\n"
        "```\n"
        "🎬 Movie : #TITLE\n"
        "📅 Year : #YEAR\n"
        "⭐ Rating: #RATING\n"
        "🎭 Genre : #GENRES\n\n"
        "Join Now : @Channel_Username\n"
        "```\n\n"
        "🔘 **--Current Caption :--**\n"
        f"{current_block}\n\n"
        "📌 /show_custom_caption — View saved captions\n\n"
        "🗑️ /delete_custom_caption — Delete a caption & restore default\n\n"
        f"**--__Please sent your {name} Custom Caption Here.__--** ⬇️"
    )


def _format_current(source, template):
    name = SOURCE_NAMES[source]
    if template:
        return f"**--{name}:--**\n```\n{template}\n```"
    return f"**--{name}: Default--** — __no custom caption saved.__"


@Client.on_message(filters.command("show_custom_caption"))
async def show_custom_caption_command(client, message):
    """/show_custom_caption - shows this user's currently saved custom
    caption for both IMDb and TMDb (or "Default" for whichever source
    has none saved)."""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    imdb_caption = await get_custom_caption(user_id, "imdb")
    tmdb_caption = await get_custom_caption(user_id, "tmdb")

    text = (
        "✏️ **--Your Custom Captions--**\n\n"
        f"{_format_current('imdb', imdb_caption)}\n\n"
        f"{_format_current('tmdb', tmdb_caption)}\n\n"
        "Open ⚙️ Settings → 🎥 IMDb / 📽 TMDb → ✏️ Custom Caption to change "
        "these, or /delete_custom_caption to remove one."
    )

    await message.reply_text(text)


@Client.on_message(filters.command("delete_custom_caption"))
async def delete_custom_caption_command(client, message):
    """/delete_custom_caption - removes a saved custom caption and
    reverts that source back to the default caption. If a template is
    saved for only one source, that one is removed directly; if both are
    saved, asks which one(s) via delete_custom_caption_keyboard()
    (handled in plugins/callback.py's "delcap_" branch)."""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    imdb_caption = await get_custom_caption(user_id, "imdb")
    tmdb_caption = await get_custom_caption(user_id, "tmdb")

    if not imdb_caption and not tmdb_caption:
        await message.reply_text("You don't have any custom captions saved yet.")
        return

    if imdb_caption and not tmdb_caption:
        await delete_custom_caption(user_id, "imdb")
        await message.reply_text(
            "🗑 Your IMDb custom caption has been removed — back to default."
        )
        return

    if tmdb_caption and not imdb_caption:
        await delete_custom_caption(user_id, "tmdb")
        await message.reply_text(
            "🗑 Your TMDb custom caption has been removed — back to default."
        )
        return

    # Both saved - ask which one(s) to remove.
    await message.reply_text(
        "You have a custom caption saved for both IMDb and TMDb — which "
        "would you like to remove?",
        reply_markup=delete_custom_caption_keyboard(),
    )


@Client.on_message(filters.text & filters.private)
async def receive_custom_caption(client, message):
    """Catches the next plain-text message from a user who just tapped
    "✏️ Custom Caption" (see set_awaiting_custom_caption() in
    plugins/callback.py) and saves it as their new template for that
    source. Does nothing at all for anyone not currently in that state -
    so this never interferes with anything else in the bot (search runs
    through Telegram's inline mode, not plain messages - see
    keyboards/home.py - so there's no other flow expecting free-text
    replies to collide with).

    ⚠️ IMPORTANT: this filter (filters.text & filters.private) matches
    EVERY private text message, including every other command
    (/start, /watchlist, /stats, /thismonth, /broadcast, ...) - Pyrogram
    only calls the FIRST matching on_message handler for a given update
    within a group and then stops, regardless of plugin load order,
    unless that handler explicitly raises ContinuePropagation. So every
    branch below that doesn't actually consume this message as a caption
    template raises ContinuePropagation() instead of returning plainly -
    this is what lets /start etc. keep working normally no matter which
    plugin file happens to load first.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        raise ContinuePropagation

    source = get_awaiting_custom_caption(user_id)
    if not source:
        raise ContinuePropagation

    text = message.text or ""

    if text.startswith("/"):
        # A command came in while "awaiting" - leave the state alone (it
        # might be unrelated) and let that command's own handler deal
        # with it; a command should never itself be saved as a caption
        # template.
        raise ContinuePropagation

    # Strip stray leading/trailing spaces per line before saving - mobile
    # keyboards commonly leave a trailing space right before Enter is
    # pressed, which would otherwise be saved as an unwanted one-space
    # indent on the next line (see utils/formatter.py's
    # render_custom_caption(), which normalizes the same way as a
    # defensive fallback for templates already saved before this fix).
    # Fully blank lines (e.g. a spacer line before a channel handle) are
    # left untouched.
    text = "\n".join(line.strip() for line in text.split("\n"))

    clear_awaiting_custom_caption(user_id)
    await set_custom_caption(user_id, source, text)

    name = SOURCE_NAMES[source]
    await message.reply_text(
        f"✅ Your {name} custom caption is saved and will be used for "
        f"every {name} result from now on.\n\n"
        "📌 /show_custom_caption — view it anytime\n"
        "🗑 /delete_custom_caption — remove it, back to default"
    )
