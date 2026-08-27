# Location: keyboards/settings.py  (NEW FILE)

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Keyboards for the ✅ NEW ⚙️ Settings feature (see keyboards/home.py for the
# main-menu entry point, database/settings_db.py for the field lists +
# saved on/off state, and plugins/callback.py for everything these buttons
# trigger).
# ---------------------------------------------------------------------------

# Presentational label (with emoji) for every settings field key this bot
# can show a toggle for. Shared between IMDb Settings and TMDb Settings -
# database/settings_db.py's IMDB_FIELD_ORDER / TMDB_FIELD_ORDER decides
# which of these keys actually apply to (and are drawn for) each source.
FIELD_LABELS = {
    "poster": "🖼 Poster",
    "title": "🏷 Title",
    "year": "📅 Year",
    "runtime": "⏱ Runtime",
    "genres": "🎭 Genres",
    "seasons": "📊 Seasons",
    "episodes": "📺 Episodes",
    "rating": "⭐ Rating",
    "language": "🗣 Language",
    "country": "🌍 Country",
    "director": "🎬 Director",
    "writers": "✍️ Writers",
    "cast": "🎟 Cast",
    "plot": "📝 Plot",
}


def settings_menu_keyboard():
    """Shown right after tapping "⚙️ Settings" on the main menu.

    Two options:
      - 📽 TMDb Settings -> per-field toggles for SEARCH - TMDb details
      - 🎥 IMDb Settings -> per-field toggles for SEARCH - IMDb details
      - ⬅ Back           -> back to the bot's main menu (callback_data
                            "back_home", already handled in
                            plugins/callback.py)
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📽 TMDb Settings", callback_data="settings_tmdb_open")],
            [InlineKeyboardButton("🎥 IMDb Settings", callback_data="settings_imdb_open")],
            [InlineKeyboardButton("⬅ Back", callback_data="back_home")],
        ]
    )


def _source_settings_keyboard(source, field_order, current_settings):
    """Shared builder for imdb_settings_keyboard()/tmdb_settings_keyboard()
    below - one ✅/❌ toggle button per field this source's API actually
    provides (see database/settings_db.py's IMDB_FIELD_ORDER /
    TMDB_FIELD_ORDER), 2 per row, plus a "⬅ Back" button that returns to
    the Settings menu (NOT the main menu).

    Each button's callback_data is "set_<source>_toggle_<field>" -
    plugins/callback.py flips that field for this user
    (database/settings_db.py's toggle_field()) and redraws this same
    keyboard in place, so the ✅/❌ icon updates immediately on tap.

    ✅ NEW - ✏️ Custom Caption feature: also adds a full-width
    "✏️ Custom Caption" row just above "⬅ Back" - callback_data
    "custom_caption_<source>_open", opens the page where this user can
    replace this source's whole caption with their own template (see
    keyboards/custom_caption.py, plugins/custom_caption.py, and
    plugins/callback.py). Independent of the per-field toggles above:
    those still control the Poster attachment either way, but have no
    effect on the caption text once a custom template is saved.
    """
    rows = []
    row = []

    for key in field_order:
        label = FIELD_LABELS.get(key, key.title())
        enabled = current_settings.get(key, True)
        icon = "✅" if enabled else "❌"

        row.append(
            InlineKeyboardButton(
                f"{icon} {label}", callback_data=f"set_{source}_toggle_{key}"
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [InlineKeyboardButton("✏️ Custom Caption", callback_data=f"custom_caption_{source}_open")]
    )
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="settings_open")])

    return InlineKeyboardMarkup(rows)


def imdb_settings_keyboard(field_order, current_settings):
    return _source_settings_keyboard("imdb", field_order, current_settings)


def tmdb_settings_keyboard(field_order, current_settings):
    return _source_settings_keyboard("tmdb", field_order, current_settings)

