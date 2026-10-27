"""Hebrew + Gregorian date formatting (uses pyluach).

Exposed to templates as ``heb_full``, ``heb_short`` and ``greg``.
"""
from __future__ import annotations

from datetime import date

try:
    from pyluach import dates as _pl_dates
except Exception:  # pragma: no cover - pyluach should always be installed
    _pl_dates = None


def hebrew_date_string(d: date) -> str:
    """Full Hebrew date, e.g. 'י״ד בחשוון תשפ״ו'."""
    if _pl_dates is None:
        return ""
    try:
        return _pl_dates.HebrewDate.from_pydate(d).hebrew_date_string()
    except Exception:
        return ""


def hebrew_day_month(d: date) -> str:
    """Short Hebrew date without the year, e.g. 'י״ד חשוון'."""
    full = hebrew_date_string(d)
    if not full:
        return ""
    tokens = full.split()
    if len(tokens) < 2:
        return full
    day, month = tokens[0], tokens[1]
    # Drop a leading "ב" preposition from the month ("בחשוון" -> "חשוון").
    if len(month) > 1 and month[0] == "ב":
        month = month[1:]
    return f"{day} {month}"


def format_greg(d: date, with_year: bool = False) -> str:
    """Gregorian date, e.g. '25.10' or '25.10.2026'."""
    return d.strftime("%d.%m.%Y") if with_year else d.strftime("%d.%m")
