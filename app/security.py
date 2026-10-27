"""Edit-access gate. Viewing is open; editing needs the shared password."""
from __future__ import annotations

from functools import wraps
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask import abort, current_app, redirect, request, session, url_for


def local_redirect_target(value: str | None) -> str:
    """Accept only absolute local paths, never external redirect targets."""
    fallback = url_for("schedule.index")
    if not value or not value.startswith("/") or value.startswith("//"):
        return fallback
    if "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return fallback
    try:
        parsed = urlsplit(value)
    except ValueError:
        return fallback
    if parsed.scheme or parsed.netloc:
        return fallback
    group = request.args.get("groupId")
    if group:
        query = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=True) if key != "groupId"]
        query.append(("groupId", group))
        return urlunsplit(("", "", parsed.path, urlencode(query), parsed.fragment))
    return value


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
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapper
