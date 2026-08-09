# Location: database/settings_db.py  (NEW FILE)

from database.mongo import settings_collection

# ---------------------------------------------------------------------------
# ✅ NEW - ⚙️ Settings feature (IMDb Settings / TMDb Settings)
#
# Lets each user toggle, per source, which detail fields show up in the
# movie/series details caption built by utils/formatter.py's
# format_imdb_details() - see plugins/details.py, which reads these
# settings before rendering every IMDb/TMDb details page, and
# plugins/callback.py, which wires up the ⚙️ Settings menu itself.
#
# Only fields this bot actually fetches with real data are listed below -
# see services/imdb.py + services/tmdb.py for what each source provides.
# Fields the current IMDb API never returns (Vote Count, Content Rating,
# Language, Country, Awards) and fields TMDb never returns (Vote Count,
# Content Rating, Awards) are intentionally left out of these lists - they
# already never appear in the caption (utils/formatter.py skips any field
# that comes back "N/A" regardless of these settings), so there is nothing
# meaningful to toggle for them.
#
# One MongoDB document per user (settings_collection, database/mongo.py):
#   {"user_id": ..., "imdb_fields": {...}, "tmdb_fields": {...}}
# A field missing from a saved document (new user, or a field added to the
# lists below after they last changed anything) defaults to enabled (True)
# - this is what keeps the feature purely additive: a user who never opens
# ⚙️ Settings sees every field exactly as before.
# ---------------------------------------------------------------------------

# Order also decides the order fields are drawn on each Settings page
# (keyboards/settings.py).
IMDB_FIELD_ORDER = [
    "poster",
    "title",
    "year",
    "runtime",
    "genres",
    "rating",
    "director",
    "writers",
    "cast",
    "plot",
]

TMDB_FIELD_ORDER = [
    "poster",
    "title",
    "year",
    "runtime",
    "genres",
    "seasons",
    "episodes",
    "rating",
    "language",
    "country",
    "director",
    "writers",
    "cast",
    "plot",
]


def _field_order(source):
    return IMDB_FIELD_ORDER if source == "imdb" else TMDB_FIELD_ORDER


def _defaults(source):
    return {key: True for key in _field_order(source)}


async def get_settings(user_id, source):
    """Return this user's saved on/off state for every `source`
    ("imdb"/"tmdb") field, defaulting anything unsaved (or any field added
    to IMDB_FIELD_ORDER/TMDB_FIELD_ORDER since they last changed a
    setting) to enabled.

    `user_id` may be None (e.g. an inline query fired with no from_user) -
    returns all-enabled defaults in that case without touching the
    database, same fallback pattern used elsewhere in this bot (see
    plugins/details.py's `if user_id else False` checks).
    """
    defaults = _defaults(source)

    if not user_id:
        return defaults

    doc = await settings_collection.find_one({"user_id": user_id})
    if not doc:
        return defaults

    saved = doc.get(f"{source}_fields") or {}

    merged = dict(defaults)
    for key in merged:
        if key in saved:
            merged[key] = bool(saved[key])

    return merged


async def toggle_field(user_id, source, field):
    """Flip one field on/off for this user and persist it immediately, so
    it's in effect for every IMDb/TMDb result from this point on -
    including ones already in this chat if reopened - and still in effect
    on the user's next session (bot restart, new chat, etc).

    Returns the user's full updated settings dict for `source`. If `field`
    isn't a real field for this source, the settings are returned
    unchanged (nothing is written).
    """
    current = await get_settings(user_id, source)

    if field not in current:
        return current

    new_value = not current[field]

    await settings_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"{source}_fields.{field}": new_value}},
        upsert=True,
    )

    current[field] = new_value
    return current


# ---------------------------------------------------------------------------
# ✅ NEW - ✏️ Custom Caption feature
#
# Lets each user fully replace the field-by-field caption built by
# utils/formatter.py's format_imdb_details() with their own template, per
# source ("imdb"/"tmdb") - built from the #TAG placeholders listed in
# plugins/custom_caption.py, plus any of their own text (channel name,
# username, etc). See utils/formatter.py's render_custom_caption(), which
# fills a saved template in, and plugins/details.py's _resolve_display(),
# which decides (per source) whether to use it instead of the normal
# caption for a given user.
#
# Stored on the SAME per-user document as the field toggles above
# ({"user_id": ..., "imdb_fields": {...}, "tmdb_fields": {...},
# "imdb_custom_caption": "...", "tmdb_custom_caption": "..."}). A user
# with no saved template for a source simply has no
# "<source>_custom_caption" key at all - get_custom_caption() below
# treats that (and an empty string) the same: "use the default caption".
# ---------------------------------------------------------------------------


async def get_custom_caption(user_id, source):
    """Return this user's saved custom caption template for `source`
    ("imdb"/"tmdb"), or None if they've never saved one. Callers treat
    None as "use the normal field-by-field caption" (see
    plugins/details.py). Same user_id=None fallback as get_settings()
    above - returns None without touching the database.
    """
    if not user_id:
        return None

    doc = await settings_collection.find_one({"user_id": user_id})
    if not doc:
        return None

    return doc.get(f"{source}_custom_caption") or None


async def set_custom_caption(user_id, source, template):
    """Save/replace this user's custom caption template for `source` -
    used for every future IMDb/TMDb result from this point on. See
    plugins/custom_caption.py's receive_custom_caption(), which collects
    the template text from the user and calls this.
    """
    await settings_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"{source}_custom_caption": template}},
        upsert=True,
    )


async def delete_custom_caption(user_id, source):
    """Remove this user's saved custom caption template for `source`,
    reverting them back to the normal field-by-field caption (still
    respecting whatever field toggles they've set above). Safe to call
    even if nothing was ever saved for this source.
    """
    await settings_collection.update_one(
        {"user_id": user_id},
        {"$unset": {f"{source}_custom_caption": ""}},
    )
