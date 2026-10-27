from __future__ import annotations

from datetime import datetime, timedelta

from app.extensions import db


class Week(db.Model):
    """A single schedulable week, identified by its Sunday start date."""

    __tablename__ = "weeks"

    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, unique=True, nullable=False, index=True)  # Sunday
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(120))

    slots = db.relationship(
        "Slot",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="Slot.day_index, Slot.shift",
    )

    @property
    def end_date(self):
        return self.start_date + timedelta(days=6)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Week {self.start_date}>"
