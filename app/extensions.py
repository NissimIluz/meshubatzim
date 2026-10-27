"""Shared extension instances.

Kept in their own module so any layer can import them without triggering a
circular import with the application factory.
"""
from __future__ import annotations

from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
# async_mode / message_queue are configured at init time in the app factory.
socketio = SocketIO()
