"""Centralized logging: writes to the ``logs`` table and to stdout.

Logging failures must never break a request, so DB writes are guarded.
"""
from __future__ import annotations

import logging

from app.extensions import db
from app.models import Log

_py_logger = logging.getLogger("meshubatzim")


def write_log(
    level: str,
    category: str,
    *,
    message: str | None = None,
    detail: str | None = None,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    duration_ms: int | None = None,
    ip: str | None = None,
    user: str | None = None,
) -> None:
    # Always mirror to stdout (captured by Render / the terminal).
    _py_logger.log(
        getattr(logging, level.upper(), logging.INFO),
        "[%s] %s", category, message or path or "",
    )
    try:
        db.session.add(
            Log(
                level=level.upper(),
                category=category,
                message=message,
                detail=detail,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                ip=ip,
                user=user,
            )
        )
        db.session.commit()
    except Exception:  # pragma: no cover - logging must be non-fatal
        db.session.rollback()


def log_event(category: str, message: str, level: str = "INFO", **extra) -> None:
    """Convenience wrapper for application/realtime events."""
    detail = None
    if extra:
        import json

        detail = json.dumps(extra, ensure_ascii=False, default=str)
    write_log(level, category, message=message, detail=detail)
