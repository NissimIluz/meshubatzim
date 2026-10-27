"""Israeli-week helpers. Week starts on Sunday (day_index 0)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

_DEFAULT_TZ = "Asia/Jerusalem"


def _today() -> date:
    tz_name = _DEFAULT_TZ
    try:  # use configured timezone when inside an app context
        from flask import current_app

        tz_name = current_app.config.get("TIMEZONE", _DEFAULT_TZ)
    except Exception:
        pass
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            pass
    return date.today()


def day_index_of(d: date) -> int:
    """0 = Sunday ... 6 = Saturday."""
    return (d.weekday() + 1) % 7


def sunday_of(d: date) -> date:
    """Return the Sunday that starts the week containing ``d``."""
    return d - timedelta(days=day_index_of(d))


def current_week_start() -> date:
    return sunday_of(_today())


def week_dates(start: date) -> list[date]:
    """The 7 dates of the week beginning at ``start`` (Sunday)."""
    return [start + timedelta(days=i) for i in range(7)]


def add_weeks(start: date, n: int) -> date:
    return start + timedelta(weeks=n)


def parse_date(value: str | None) -> date | None:
    """Parse an exact YYYY-MM-DD date (no week normalization). None if invalid."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_week_param(value: str | None) -> date | None:
    """Parse a ?week=YYYY-MM-DD param and normalize to the week's Sunday.

    Returns None for missing/invalid input (caller falls back to current week).
    """
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return sunday_of(parsed)
