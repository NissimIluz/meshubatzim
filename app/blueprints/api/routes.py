from __future__ import annotations

from datetime import date

from flask import (
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
)

from app.blueprints.api import api_bp
from app.extensions import socketio
from app.identity import current_actor
from app.realtime import room_for_week
from app.security import edit_required, local_redirect_target
from app.services import recurring_service, rules_service, slot_service, week_service
from app.utils.week_utils import parse_date, parse_week_param


@api_bp.route("/slot", methods=["POST"])
@edit_required
def update_slot():
    target = parse_week_param(request.form.get("week"))
    if target is None:
        return "bad week", 400
    try:
        day_index = int(request.form.get("day_index", ""))
    except (TypeError, ValueError):
        return "bad day_index", 400
    shift = request.form.get("shift", "")

    week = week_service.get_week(target)
    if week is None:
        if week_service.is_creatable(target):
            week = week_service.create_week(target)
        else:
            return "week not editable", 400

    actor = current_actor()
    try:
        slot = slot_service.update_slot(
            week,
            day_index,
            shift,
            request.form.get("assignee", ""),
            request.form.get("notes", ""),
            user=actor,
        )
    except ValueError:
        return "bad shift", 400

    room = room_for_week(target.isoformat())
    # Persisted -> broadcast the new state to everyone viewing this week.
    socketio.emit(
        "slot_updated",
        {"week": target.isoformat(), "editor": actor, **slot.to_dict()},
        room=room,
    )

    # Optional linking rules (fail-safe): broadcast any mirrored cells too.
    for extra in rules_service.apply_rules(week, slot):
        socketio.emit(
            "slot_updated",
            {"week": target.isoformat(), "editor": actor, **extra.to_dict()},
            room=room,
        )

    # HTMX swaps the cell with the fresh server-rendered fragment.
    return render_template(
        "schedule/_cell.html",
        slot=slot,
        day=day_index,
        shift=shift,
        week_key=target.isoformat(),
    )


@api_bp.route("/recurring", methods=["POST"])
@edit_required
def set_recurring():
    try:
        day_index = int(request.form.get("day_index", ""))
    except (TypeError, ValueError):
        return "bad day_index", 400
    shift = request.form.get("shift", "")
    if shift not in current_app.config["SHIFT_NAMES"] or not (0 <= day_index <= 6):
        return "bad cell", 400

    effective_from = parse_date(request.form.get("effective_from")) or date.today()
    effective_until = parse_date(request.form.get("effective_until"))  # None = forever

    recurring_service.set_template(
        day_index,
        shift,
        request.form.get("assignee", ""),
        request.form.get("notes", ""),
        effective_from,
        effective_until=effective_until,
    )

    # HTMX submit -> no page reload: 204 + a client event to close + toast.
    if request.headers.get("HX-Request"):
        resp = make_response("", 204)
        resp.headers["HX-Trigger"] = "recurring-saved"
        return resp

    # No-JS fallback: flash + redirect (full reload).
    flash("נשמר כקבוע (חוזר). יועתק אוטומטית ללוחות חדשים.")
    return redirect(local_redirect_target(request.form.get("next")))
