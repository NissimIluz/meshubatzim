"""Error handlers that log to the ``logs`` table and render Hebrew error pages."""
from __future__ import annotations

import traceback

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.identity import current_actor
from app.services.log_service import write_log


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/error.html", code=403,
                               message="אין הרשאת עריכה. יש להזדהות כדי לערוך."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/error.html", code=404,
                               message="הדף לא נמצא."), 404

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        # Let other HTTP exceptions keep their native status/response.
        if isinstance(e, HTTPException):
            return e

        db.session.rollback()
        write_log(
            "ERROR",
            "error",
            method=request.method,
            path=request.path,
            status_code=500,
            message=str(e),
            detail=traceback.format_exc(),
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            user=current_actor(),
        )
        return render_template("errors/error.html", code=500,
                               message="אירעה שגיאה במערכת. נסו שוב מאוחר יותר."), 500
