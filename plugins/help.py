# Location: plugins/help.py  (NEW FILE)

from pyrogram import Client, filters

from about.about_info import build_help_text
from keyboards.about import help_keyboard

print("✅ HELP PLUGIN LOADED")


# ✅ NEW - /help command. Previously there was no /help command handler
# at all, so a user typing /help got no response (or Telegram's default
# "unknown command" behaviour). This now sends the EXACT same "❓ Help —
# What This Bot Can Do" feature guide as the "❓ Help" button on the
# "ℹ️ About" page (callback_data "help_open", handled in
# plugins/callback.py) - the text itself lives in about/about_info.py's
# build_help_text(), the single source of truth already used by that
# button, so both entry points (typing /help and tapping the button)
# always show identical text and stay in sync automatically.
#
# Also reuses keyboards/about.py's help_keyboard(), so the "⬅ Back"
# button under this message behaves the same way it does when Help is
# opened from the About page - tapping it edits THIS message into the
# "ℹ️ About" page (plugins/callback.py's "about_open" handler just edits
# whatever message the tapped button is attached to).
@Client.on_message(filters.command("help"))
async def help_command(client, message):

    print("✅ /help COMMAND RECEIVED")

    await message.reply_text(
        text=build_help_text(),
        reply_markup=help_keyboard(),
        disable_web_page_preview=True,
    )
