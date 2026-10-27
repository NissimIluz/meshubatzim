from __future__ import annotations

from datetime import datetime

from app.extensions import db


class RecurringTemplate(db.Model):
    """A "from now on" default for a given (day, shift) cell.

    When a new week is created, each cell is pre-filled from the active
    template whose ``effective_from`` is on or before that week's start date.
    """

    __tablename__ = "recurring_templates"

    id = db.Column(db.Integer, primary_key=True)
    day_index = db.Column(db.Integer, nullable=False)  # 0=Sunday .. 6=Saturday
    shift = db.Column(db.String(16), nullable=False)   # 'morning' | 'evening'
    assignee = db.Column(db.String(120))
    notes = db.Column(db.Text)
    effective_from = db.Column(db.Date, nullable=False, index=True)
    effective_until = db.Column(db.Date)  # null = forever
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(120))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Recurring d={self.day_index} {self.shift} from {self.effective_from}>"
