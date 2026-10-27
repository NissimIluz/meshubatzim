"""Actor identity.

Editing is currently open (no login), so we do not know who performs each
action — it is recorded as "unknown" (לא ידוע). The DB keeps the columns ready
(updated_by / created_by) so that when mandatory login is added later, real
identity can be implemented here without touching the callers.
"""
from __future__ import annotations

from flask import has_request_context

UNKNOWN_ACTOR = "לא ידוע"


def current_actor() -> str:
    """Who is acting now. Always 'unknown' until login is implemented."""
    return UNKNOWN_ACTOR


def actor_or_system() -> str:
    """Like current_actor(), but 'system' outside a request (CLI/seed)."""
    return current_actor() if has_request_context() else "system"
