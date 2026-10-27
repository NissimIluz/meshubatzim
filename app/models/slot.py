from __future__ import annotations

from datetime import datetime

from app.extensions import db


class Slot(db.Model):
    """One cell of the board: a (week, day, shift) assignment."""

    __tablename__ = "slots"

    id = db.Column(db.Integer, primary_key=True)
    week_id = db.Column(
        db.Integer,
        db.ForeignKey("weeks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_index = db.Column(db.Integer, nullable=False)  # 0=Sunday .. 6=Saturday
    shift = db.Column(db.String(16), nullable=False)   # 'morning' | 'evening'
    assignee = db.Column(db.String(120))
    notes = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = db.Column(db.String(120))

    week = db.relationship("Week", back_populates="slots")

    __table_args__ = (
        db.UniqueConstraint("week_id", "day_index", "shift", name="uq_slot_cell"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "week_id": self.week_id,
            "day_index": self.day_index,
            "shift": self.shift,
            "assignee": self.assignee or "",
            "notes": self.notes or "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Slot w={self.week_id} d={self.day_index} {self.shift}>"
