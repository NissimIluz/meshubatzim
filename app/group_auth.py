"""Require the configured groupId on every HTTP/Socket.IO transport request."""
from hmac import compare_digest
from urllib.parse import parse_qs

from flask import has_request_context, request
from werkzeug.wrappers import Response


def valid_group_id(config, values) -> bool:
    expected = config.get("GROUP_ID", "")
    return bool(expected) and len(values) == 1 and compare_digest(
        values[0].encode("utf-8"), expected.encode("utf-8")
    )


def register_group_auth(app):
    downstream = app.wsgi_app

    def require_group(environ, start_response):
        values = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).get("groupId", [])
        if not valid_group_id(app.config, values):
            response = Response("Forbidden", status=403, content_type="text/plain; charset=utf-8")
            response.headers["Cache-Control"] = "no-store"
            return response(environ, start_response)
        return downstream(environ, start_response)

    app.wsgi_app = require_group

    @app.url_defaults
    def preserve_group(endpoint, values):
        if has_request_context():
            groups = request.args.getlist("groupId")
            if valid_group_id(app.config, groups):
                values["groupId"] = groups[0]

    @app.after_request
    def protect_group_url(response):
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        return response
