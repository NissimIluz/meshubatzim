"""Production entry point (gunicorn).

    gunicorn --worker-class gthread --workers 1 --threads 8 \
             --bind 0.0.0.0:$PORT wsgi:app
"""
from app import create_app, socketio  # noqa: F401  (socketio imported for side effects)

app = create_app()
