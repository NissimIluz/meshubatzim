from __future__ import annotations

from datetime import timedelta

from flask import render_template, request

from app.blueprints.schedule import schedule_bp
from app.services import slot_service, week_service
from app.utils.week_utils import current_week_start, parse_week_param, week_dates


@schedule_bp.route("/")
def index():
    target = parse_week_param(request.args.get("week")) or current_week_start()
    week, created, creatable = week_service.get_week_for_view(target)
    matrix = slot_service.slots_matrix(week) if week else {}

    return render_template(
        "schedule/index.html",
        week_start=target,
        week_end=target + timedelta(days=6),
        dates=week_dates(target),
        matrix=matrix,
        week_obj=week,
        created=created,
        creatable=creatable,
        out_of_range=week is None,
        week_key=target.isoformat(),
        prev_week=(target - timedelta(weeks=1)).isoformat(),
        next_week=(target + timedelta(weeks=1)).isoformat(),
        is_current=target == current_week_start(),
        this_week_key=current_week_start().isoformat(),
    )
