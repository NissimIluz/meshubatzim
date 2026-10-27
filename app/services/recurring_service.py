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
