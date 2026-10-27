"""Slot (cell) reads and writes."""
from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.models import Slot, Week


def slots_matrix(week: Week) -> dict[tuple[int, str], Slot]:
    """Map (day_index, shift) -> Slot for quick template lookup."""
    return {(s.day_index, s.shift): s for s in week.slots}


def get_slot(week: Week, day_index: int, shift: str) -> Slot | None:
    return Slot.query.filter_by(
        week_id=week.id, day_index=day_index, shift=shift
    ).first()


def update_slot(
    week: Week,
    day_index: int,
    shift: str,
    assignee: str | None,
    notes: str | None,
    user: str | None = None,
) -> Slot:
    """Create or update a cell. Raises ValueError on invalid shift."""
    if shift not in current_app.config["SHIFT_NAMES"]:
        raise ValueError(f"invalid shift: {shift!r}")

    slot = get_slot(week, day_index, shift)
    if slot is None:
        slot = Slot(week_id=week.id, day_index=day_index, shift=shift)
        db.session.add(slot)

    slot.assignee = (assignee or "").strip() or None
    slot.notes = (notes or "").strip() or None
    slot.updated_by = user
    db.session.commit()

    # Linked-cell automation (e.g. Friday-evening <-> Shabbat) is handled by
    # rules_service.apply_rules(), driven by the RULES env config, and invoked
    # by the API route after this primary save so it can broadcast the extras.

    return slot
