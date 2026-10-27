"""Edit-access gate. Viewing is open; editing needs the shared password."""
from __future__ import annotations

from functools import wraps

from flask import abort, current_app, redirect, request, session, url_for


def can_edit() -> bool:
    """True if the current session may edit the board."""
    cfg = current_app.config
    # Open-edit mode: everyone can edit, no password (login stays inactive).
    if cfg["OPEN_EDIT"]:
        return True
    if session.get("can_edit"):
        return True
    # Dev convenience: if no password is set, editing is open in debug only.
    if not cfg["EDIT_PASSWORD"] and cfg.get("DEBUG"):
        return True
    return False


def edit_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not can_edit():
            if request.path.startswith("/api") or request.headers.get("HX-Request"):
                abort(403)
            return redirect(url_for("auth.login", next=request.url))
        return view(*args, **kwargs)

    return wrapper
