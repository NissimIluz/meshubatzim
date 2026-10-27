"""Jinja globals/helpers available in every template."""
from __future__ import annotations

from datetime import date

from flask import Flask

from app import constants
from app.security import can_edit
from app.utils import hebrew_dates, week_utils


def register_context(app: Flask) -> None:
    app.jinja_env.globals.update(
        DAY_NAMES_HE=constants.DAY_NAMES_HE,
        DAY_COLORS=constants.DAY_COLORS,
        SHIFTS=app.config["SHIFTS"],
        SHIFT_KEYS=app.config["SHIFT_NAMES"],
        heb_full=hebrew_dates.hebrew_date_string,
        heb_short=hebrew_dates.hebrew_day_month,
        greg=hebrew_dates.format_greg,
        day_name=lambda i: constants.DAY_NAMES_HE[i],
    )

    @app.context_processor
    def inject_globals():
        cfg = app.config
        return {
            "app_title": cfg["APP_TITLE"],
            "important_notes": cfg["IMPORTANT_NOTES"],
            "shift_labels": cfg["SHIFT_LABELS"],
            "active_days": cfg["ACTIVE_DAYS"],
            "can_edit": can_edit(),
            "edit_gate_on": not cfg["OPEN_EDIT"],
            "today": date.today(),
            "current_week_start": week_utils.current_week_start(),
        }
