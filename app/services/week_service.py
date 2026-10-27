"""Week lifecycle: lazy creation (up to N weeks ahead) + recurring pre-fill."""
from __future__ import annotations

from datetime import date

from flask import current_app

from app.extensions import db
from app.identity import actor_or_system
from app.models import Slot, Week
from app.services import recurring_service
from app.services.log_service import log_event
from app.utils.week_utils import add_weeks, current_week_start


def get_week(start_date: date) -> Week | None:
    return Week.query.filter_by(start_date=start_date).first()


def is_creatable(start_date: date) -> bool:
    """True if this week may be created now (current week .. +MAX_WEEKS_AHEAD)."""
    current = current_week_start()
    max_ahead = current_app.config["MAX_WEEKS_AHEAD"]
    return current <= start_date <= add_weeks(current, max_ahead)


def create_week(
    start_date: date, apply_recurring: bool = True, created_by: str | None = None
) -> Week:
    """Create a week and its slots, pre-filling from recurring templates."""
    week = Week(start_date=start_date, created_by=created_by or actor_or_system())
    db.session.add(week)
    db.session.flush()  # assign week.id

    active_days = current_app.config["ACTIVE_DAYS"]
    shift_names = current_app.config["SHIFT_NAMES"]
    for day in active_days:
        for shift in shift_names:
            assignee = notes = None
            if apply_recurring:
                tmpl = recurring_service.get_template_for(day, shift, start_date)
                if tmpl:
                    assignee, notes = tmpl.assignee, tmpl.notes
            db.session.add(
                Slot(
                    week_id=week.id,
                    day_index=day,
                    shift=shift,
                    assignee=assignee,
                    notes=notes,
                    updated_by="system",
                )
            )
    db.session.commit()
    log_event("app", f"Created week {start_date}")
    return week


def get_or_create_week(start_date: date, apply_recurring: bool = True) -> Week:
    return get_week(start_date) or create_week(start_date, apply_recurring)


def get_week_for_view(start_date: date) -> tuple[Week | None, bool, bool]:
    """Resolve a week for display.

    Returns (week_or_None, was_created, is_creatable). A None week means the
    week does not exist and is outside the creation window -> read-only empty.
    """
    week = get_week(start_date)
    if week:
        return week, False, True
    if is_creatable(start_date):
        return create_week(start_date), True, True
    return None, False, False
