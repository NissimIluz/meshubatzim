"""Logs every (non-skipped) request into the ``logs`` table."""
from __future__ import annotations

import time

from flask import Flask, g, request

from app.identity import current_actor
from app.services.log_service import write_log


def register_request_logging(app: Flask) -> None:
    skip_prefixes = tuple(app.config["LOG_SKIP_PREFIXES"])
    enabled = app.config["LOG_REQUESTS"]

    @app.before_request
    def _start_timer() -> None:
        g._req_start = time.perf_counter()

    @app.after_request
    def _log_request(response):
        if not enabled:
            return response
        path = request.path or ""
        if path.startswith(skip_prefixes):
            return response

        start = getattr(g, "_req_start", None)
        duration_ms = int((time.perf_counter() - start) * 1000) if start else None

        write_log(
            "INFO",
            "request",
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            user=current_actor(),
        )
        return response
