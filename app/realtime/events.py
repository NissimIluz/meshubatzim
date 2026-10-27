"""SocketIO event handlers: per-week rooms + live presence.

Presence is tracked in-memory (per process). This is correct for a single
worker. To scale beyond one instance, set REDIS_URL (SocketIO message queue)
AND move this presence store to Redis.
"""
from __future__ import annotations

import threading

from flask import request
from flask_socketio import emit, join_room, leave_room

from app.extensions import socketio
from app.realtime import room_for_week

_lock = threading.Lock()
_room_members: dict[str, set[str]] = {}
_sid_room: dict[str, str] = {}


def _count(room: str) -> int:
    return len(_room_members.get(room, ()))


@socketio.on("join")
def on_join(data):
    week = (data or {}).get("week")
    if not week:
        return
    room = room_for_week(week)
    sid = request.sid
    prev = None
    with _lock:
        prev = _sid_room.get(sid)
        if prev and prev != room:
            leave_room(prev)
            _room_members.get(prev, set()).discard(sid)
        join_room(room)
        _room_members.setdefault(room, set()).add(sid)
        _sid_room[sid] = room

    emit("presence", {"count": _count(room)}, to=room)
    if prev and prev != room:
        emit("presence", {"count": _count(prev)}, to=prev)


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    with _lock:
        room = _sid_room.pop(sid, None)
        if room:
            _room_members.get(room, set()).discard(sid)
    if room:
        emit("presence", {"count": _count(room)}, to=room)
