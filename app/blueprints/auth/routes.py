from __future__ import annotations

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.blueprints.auth import auth_bp
from app.services.log_service import log_event


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.values.get("next") or url_for("schedule.index")
    if request.method == "POST":
        configured = current_app.config["EDIT_PASSWORD"]
        password = request.form.get("password", "")
        if configured and password == configured:
            session["can_edit"] = True
            log_event("app", "Edit unlocked")
            return redirect(next_url)
        flash("סיסמה שגויה", "error")
        log_event("app", "Failed edit-unlock attempt", level="WARNING")
    return render_template("auth/login.html", next_url=next_url)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("can_edit", None)
    return redirect(request.values.get("next") or url_for("schedule.index"))
