from __future__ import annotations

from datetime import datetime

from app.extensions import db


class Log(db.Model):
    """Append-only log table for requests, errors and app events."""

    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    level = db.Column(db.String(16), index=True)       # INFO | WARNING | ERROR
    category = db.Column(db.String(32), index=True)    # request | error | app | realtime
    method = db.Column(db.String(10))
    path = db.Column(db.String(300))
    status_code = db.Column(db.Integer)
    duration_ms = db.Column(db.Integer)
    ip = db.Column(db.String(64))
    user = db.Column(db.String(120))
    message = db.Column(db.Text)
    detail = db.Column(db.Text)                        # traceback / JSON extras

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Log {self.level} {self.category} {self.path}>"
