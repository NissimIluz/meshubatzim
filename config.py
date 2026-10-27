"""Application configuration.

Everything configurable lives here and is sourced from environment variables
(loaded from ``.env`` in development via python-dotenv). See ``.env.example``.
"""
from __future__ import annotations

import json
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int_list(value: str | None, default: list[int]) -> list[int]:
    if not value:
        return default
    return [int(x) for x in value.split(",") if x.strip() != ""]


def _as_str_list(value: str | None, default: list[str]) -> list[str]:
    if value is None:
        return default
    return [x.strip() for x in value.split(",") if x.strip() != ""]


_NOTE_ALIASES = {"green": "success", "ok": "success"}
_NOTE_TYPES = {"danger", "warning", "info", "success", "note"}


def _coerce_h(value) -> int | None:
    try:
        h = int(value)
    except (TypeError, ValueError):
        return None
    return h if 1 <= h <= 6 else None


def _parse_notes(raw: str | None) -> list[dict]:
    """Parse IMPORTANT_NOTE into a normalized list of note objects.

    Expected value is a JSON array of objects, each:
        {"text": str, "type": danger|warning|info|success|note, "h": 1..6}
    ``type`` and ``h`` are optional. A plain string or a single object are
    also accepted, and malformed input falls back to a single plain note.
    """
    if not raw or not raw.strip():
        return []
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return [{"text": raw, "type": "note", "h": None}]

    if isinstance(data, (dict, str)):
        data = [data]
    if not isinstance(data, list):
        return []

    notes: list[dict] = []
    for item in data:
        if isinstance(item, str):
            if item.strip():
                notes.append({"text": item.strip(), "type": "note", "h": None})
            continue
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        note_type = str(item.get("type", "note")).strip().lower()
        note_type = _NOTE_ALIASES.get(note_type, note_type)
        if note_type not in _NOTE_TYPES:
            note_type = "note"
        notes.append({"text": text, "type": note_type, "h": _coerce_h(item.get("h"))})
    return notes


_DEFAULT_SHIFTS = [
    {"name": "morning", "label": "08:00–14:00", "start": "08:00", "end": "14:00"},
    {"name": "evening", "label": "14:00–20:00", "start": "14:00", "end": "20:00"},
]


def _parse_shifts(raw: str | None) -> list[dict]:
    """Parse SHIFTS: a JSON array of shift objects.

    Each shift: {"name": str, "label": str, "start": "HH:MM", "end": "HH:MM"}.
    The number and identity of shifts are fully configurable (not fixed at 2).
    Falls back to the two default shifts for missing/invalid input.
    """
    default = [dict(s) for s in _DEFAULT_SHIFTS]
    if not raw or not raw.strip():
        return default
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return default
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return default

    shifts: list[dict] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        shifts.append({
            "name": name,
            "label": str(item.get("label", "")).strip() or name,
            "start": str(item.get("start", "")).strip(),
            "end": str(item.get("end", "")).strip(),
        })
    return shifts or default


_RULE_ACTION_ALIASES = {"addall": "mirror", "addalos": "mirror", "fill": "mirror"}
_RULE_ACTIONS = {"mirror"}


def _parse_rules(raw: str | None, valid_shifts) -> list[dict]:
    """Parse RULES: a JSON array of optional slot-linking conditions.

    Each rule: {"name": str, "action": "mirror", "targets": [{"day":0-6,
    "shift":<one of the configured shift names>}, ...]}. When any target cell
    is edited, the action is applied to the rest (mirror = copy the same
    value). Rules are best-effort: a failing rule is skipped and logged.
    """
    valid = set(valid_shifts)
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    rules: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        targets: list[dict] = []
        for t in item.get("targets") or []:
            if not isinstance(t, dict):
                continue
            try:
                day = int(t.get("day"))
            except (TypeError, ValueError):
                continue
            shift = str(t.get("shift", "")).strip()
            if not (0 <= day <= 6) or shift not in valid:
                continue
            targets.append({"day": day, "shift": shift})
        if len(targets) < 2:  # need at least two cells to link
            continue
        action = str(item.get("action", "mirror")).strip().lower()
        action = _RULE_ACTION_ALIASES.get(action, action)
        if action not in _RULE_ACTIONS:
            action = "mirror"
        rules.append({
            "name": str(item.get("name", "")).strip() or "rule",
            "action": action,
            "targets": targets,
        })
    return rules


class Config:
    """Base configuration shared by all environments."""

    # ---- Core ----
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
    APP_TITLE = os.getenv("APP_TITLE", "לוח שיבוצים שבועי אילוז ")
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Jerusalem")

    # ---- Database ----
    # Render/Heroku expose "postgres://"; SQLAlchemy needs "postgresql://".
    _db_url = os.getenv("DATABASE_URL", "sqlite:///meshubatzim.sqlite3")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # ---- Editing access ----
    # OPEN_EDIT=true  -> editing is open to everyone (no password). The login
    # mechanism stays in place but is inactive. Flip to false + set
    # EDIT_PASSWORD to re-enable the shared-password gate.
    OPEN_EDIT = _as_bool(os.getenv("OPEN_EDIT"), True)
    EDIT_PASSWORD = os.getenv("EDIT_PASSWORD", "")

    # ---- Scheduling rules ----
    MAX_WEEKS_AHEAD = int(os.getenv("MAX_WEEKS_AHEAD", "4"))
    ACTIVE_DAYS = _as_int_list(os.getenv("ACTIVE_DAYS"), [0, 1, 2, 3, 4, 5, 6])
    # Shifts are fully configurable (count and identity) via the SHIFTS env var.
    SHIFTS = _parse_shifts(os.getenv("SHIFTS"))
    SHIFT_NAMES = [s["name"] for s in SHIFTS]
    SHIFT_LABELS = {s["name"]: s["label"] for s in SHIFTS}

    # ---- Highlighted notes (banner) ----
    IMPORTANT_NOTES = _parse_notes(os.getenv("IMPORTANT_NOTE"))

    # ---- Optional slot-linking rules ----
    RULES = _parse_rules(os.getenv("RULES"), SHIFT_NAMES)

    # ---- Realtime ----
    SOCKETIO_ASYNC_MODE = os.getenv("SOCKETIO_ASYNC_MODE", "threading")
    SOCKETIO_MESSAGE_QUEUE = os.getenv("REDIS_URL") or None

    # ---- Logging ----
    LOG_REQUESTS = _as_bool(os.getenv("LOG_REQUESTS"), True)
    LOG_SKIP_PREFIXES = _as_str_list(
        os.getenv("LOG_SKIP_PREFIXES"), ["/static", "/socket.io", "/favicon"]
    )
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # ---- Session cookie hardening ----
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config() -> type[Config]:
    """Pick the config class based on APP_ENV / FLASK_ENV."""
    env = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
    return ProductionConfig if env.startswith("prod") else DevelopmentConfig
