"""Realtime package: SocketIO rooms + presence + change broadcasting."""
from __future__ import annotations


def room_for_week(week_key: str) -> str:
    """SocketIO room name for a given week (week_key = 'YYYY-MM-DD')."""
    return f"week:{week_key}"
