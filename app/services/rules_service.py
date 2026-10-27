"""Optional slot-linking rules (configured in RULES).

A rule links a group of cells. When any cell in the group is edited, the
action is applied to the rest. Currently supported action:

    mirror  -> copy the edited cell's assignee+notes to the other target cells.

Rules are *best-effort*: if applying a rule raises, its changes are rolled
back, the failure is logged, and the primary edit continues as if nothing
happened. A rule never breaks a normal save.
"""
from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.models import Slot, Week
from app.services import slot_service
from app.services.log_service import log_event


def apply_rules(week: Week, changed_slot: Slot) -> list[Slot]:
    """Apply any rules triggered by ``changed_slot``.

    Returns the list of *additional* slots changed (for broadcasting). The
    primary slot must already be committed by the caller.
    """
    rules = current_app.config.get("RULES") or []
    key = (changed_slot.day_index, changed_slot.shift)
    all_changed: list[Slot] = []

    for rule in rules:
        try:
            target_keys = [(t["day"], t["shift"]) for t in rule["targets"]]
            if key not in target_keys:
                continue

            rule_changed: list[Slot] = []
            if rule["action"] == "mirror":
                for day, shift in target_keys:
                    if (day, shift) == key:
                        continue
                    slot = slot_service.get_slot(week, day, shift)
                    if slot is None:
                        slot = Slot(week_id=week.id, day_index=day, shift=shift)
                        db.session.add(slot)
                    if (slot.assignee != changed_slot.assignee
                            or slot.notes != changed_slot.notes):
                        slot.assignee = changed_slot.assignee
                        slot.notes = changed_slot.notes
                        slot.updated_by = changed_slot.updated_by
                        rule_changed.append(slot)

            if rule_changed:
                db.session.commit()
                all_changed.extend(rule_changed)
        except Exception as exc:  # pragma: no cover - automation is optional
            db.session.rollback()
            log_event(
                "app",
                f"Rule '{rule.get('name', '?')}' skipped (failed): {exc}",
                level="WARNING",
            )

    return all_changed
