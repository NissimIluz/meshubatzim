"""Recurring ("from now on") templates for cells."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.identity import actor_or_system
from app.models import RecurringTemplate, Slot, Week
from app.services import slot_service
from app.services.log_service import log_event


def _norm(value: str | None) -> str | None:
    return (value or "").strip() or None


def get_template_for(day_index: int, shift: str, on_date: date) -> RecurringTemplate | None:
    """Latest active template whose [effective_from, effective_until] window
    contains ``on_date`` for the given cell (effective_until null = forever)."""
    return (
        RecurringTemplate.query.filter(
            RecurringTemplate.day_index == day_index,
            RecurringTemplate.shift == shift,
            RecurringTemplate.active.is_(True),
            RecurringTemplate.effective_from <= on_date,
            or_(
                RecurringTemplate.effective_until.is_(None),
                RecurringTemplate.effective_until >= on_date,
            ),
        )
        .order_by(RecurringTemplate.effective_from.desc(), RecurringTemplate.id.desc())
        .first()
    )


def set_template(
    day_index: int,
    shift: str,
    assignee: str | None,
    notes: str | None,
    effective_from: date,
    effective_until: date | None = None,
    created_by: str | None = None,
) -> RecurringTemplate:
    """Add a new active template (history is preserved)."""
    tmpl = RecurringTemplate(
        day_index=day_index,
        shift=shift,
        assignee=(assignee or "").strip() or None,
        notes=(notes or "").strip() or None,
        effective_from=effective_from,
        effective_until=effective_until,
        active=True,
        created_by=created_by or actor_or_system(),
    )
    db.session.add(tmpl)
    db.session.commit()
    log_event("app", f"Set recurring template day={day_index} shift={shift}",
              effective_from=str(effective_from))
    return tmpl


def list_templates() -> list[RecurringTemplate]:
    return (
        RecurringTemplate.query.filter_by(active=True)
        .order_by(RecurringTemplate.day_index, RecurringTemplate.shift)
        .all()
    )


def _weeks_in_window(day_index: int, effective_from: date, effective_until: date | None):
    """Existing weeks whose (day_index) cell-date falls in [from, until]."""
    low = effective_from - timedelta(days=6)  # start could be up to 6 days before
    query = Week.query.filter(Week.start_date >= low)
    if effective_until:
        query = query.filter(Week.start_date <= effective_until)
    result = []
    for week in query.order_by(Week.start_date).all():
        cell_date = week.start_date + timedelta(days=day_index)
        if cell_date < effective_from:
            continue
        if effective_until and cell_date > effective_until:
            continue
        result.append((week, cell_date))
    return result


def classify_existing(
    day_index: int, shift: str, assignee: str | None, notes: str | None,
    effective_from: date, effective_until: date | None,
) -> tuple[list[Week], list[tuple[Week, date]]]:
    """Split existing in-window target cells into empty vs. conflicting.

    - empty:    cell has no value -> will be filled.
    - conflict: cell has a different value -> needs an overwrite decision.
    Cells already equal to the template value are ignored.
    """
    want_a, want_n = _norm(assignee), _norm(notes)
    empty: list[Week] = []
    conflict: list[tuple[Week, date]] = []
    for week, cell_date in _weeks_in_window(day_index, effective_from, effective_until):
        slot = slot_service.get_slot(week, day_index, shift)
        cur_a = slot.assignee if slot else None
        cur_n = slot.notes if slot else None
        if not cur_a and not cur_n:
            empty.append(week)
        elif cur_a != want_a or cur_n != want_n:
            conflict.append((week, cell_date))
    return empty, conflict


def apply_value_to_weeks(
    weeks: list[Week], day_index: int, shift: str,
    assignee: str | None, notes: str | None, user: str | None = None,
) -> list[Slot]:
    """Set (day_index, shift) to the given value across ``weeks``. Returns changed slots."""
    want_a, want_n = _norm(assignee), _norm(notes)
    changed: list[Slot] = []
    for week in weeks:
        slot = slot_service.get_slot(week, day_index, shift)
        if slot is None:
            slot = Slot(week_id=week.id, day_index=day_index, shift=shift)
            db.session.add(slot)
        slot.assignee = want_a
        slot.notes = want_n
        slot.updated_by = user
        changed.append(slot)
    if changed:
        db.session.commit()
    return changed
