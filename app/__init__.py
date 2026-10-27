"""Application factory.

Usage:
    from app import create_app, socketio
    app = create_app()
    socketio.run(app)
"""
from __future__ import annotations

from dotenv import load_dotenv

# Load .env BEFORE importing config: config.py reads environment variables at
# import time, so the .env must already be in os.environ by then.
load_dotenv()

from flask import Flask  # noqa: E402

from config import Config, get_config  # noqa: E402
from app.extensions import csrf, db, migrate, socketio  # noqa: E402


def create_app(config_class: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    _init_extensions(app)
    _register_models()
    _register_blueprints(app)
    _register_realtime()
    _register_observability(app)
    _register_template_context(app)
    _register_cli(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    socketio.init_app(
        app,
        async_mode=app.config["SOCKETIO_ASYNC_MODE"],
        message_queue=app.config["SOCKETIO_MESSAGE_QUEUE"],
        cors_allowed_origins="*",
    )
    # SocketIO endpoints are not form posts; exempt them from CSRF.
    csrf.exempt_views = getattr(csrf, "exempt_views", set())


def _register_models() -> None:
    # Importing registers the models on the SQLAlchemy metadata (for migrations).
    from app import models  # noqa: F401


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.schedule import schedule_bp
    from app.blueprints.api import api_bp
    from app.blueprints.auth import auth_bp

    app.register_blueprint(schedule_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")


def _register_realtime() -> None:
    # Importing registers the SocketIO event handlers.
    from app.realtime import events  # noqa: F401


def _register_observability(app: Flask) -> None:
    from app.logging.request_logger import register_request_logging
    from app.logging.error_handlers import register_error_handlers

    register_request_logging(app)
    register_error_handlers(app)


def _register_template_context(app: Flask) -> None:
    from app.template_context import register_context

    register_context(app)


def _register_cli(app: Flask) -> None:
    from app.cli import register_cli

    register_cli(app)
