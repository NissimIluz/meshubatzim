"""Custom Flask CLI commands.

    flask init-db     # create all tables (handy for first local run without migrations)
    flask seed-demo   # create the current week with a few sample assignments
"""
from __future__ import annotations

import click
from flask import Flask

from app.extensions import db


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create all tables directly from the models (dev convenience)."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed-demo")
    def seed_demo() -> None:
        """Create the current week and populate a couple of demo cells."""
        from flask import current_app

        from app.services import slot_service, week_service
        from app.utils.week_utils import current_week_start

        shift_names = current_app.config["SHIFT_NAMES"]
        first = shift_names[0]
        second = shift_names[1] if len(shift_names) > 1 else shift_names[0]

        week = week_service.get_or_create_week(current_week_start())
        slot_service.update_slot(week, day_index=0, shift=first,
                                 assignee="מירית", notes="", user="seed")
        slot_service.update_slot(week, day_index=1, shift=first,
                                 assignee="מתנאל", notes="שיעור: 9:00-12:00", user="seed")
        slot_service.update_slot(week, day_index=2, shift=second,
                                 assignee="ניסים", notes="", user="seed")
        click.echo(f"Seeded demo data for week starting {week.start_date}.")
