import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Slot, Week
from app.security import local_redirect_target
from app.services import recurring_service, slot_service, week_service
from config import Config


class RegressionTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.path = Path(handle.name)
        handle.close()

        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = "sqlite:///" + self.path.as_posix()
            SOCKETIO_MESSAGE_QUEUE = None
            LOG_REQUESTS = False
            WTF_CSRF_ENABLED = False
            OPEN_EDIT = False
            EDIT_PASSWORD = "test-password"
            ACTIVE_DAYS = list(range(7))
            SHIFT_NAMES = ["morning", "evening"]
            SHIFT_LABELS = {"morning": "08:00–14:00", "evening": "14:00–20:00"}
            RULES = []

        self.app = create_app(TestConfig)
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.path.unlink()

    def test_recurring_windows_use_actual_cell_date(self):
        with self.app.app_context():
            recurring_service.set_template(
                5, "morning", "Friday only", "", date(2026, 10, 30), date(2026, 10, 30)
            )
            recurring_service.set_template(
                6, "morning", "Expired Monday", "", date(2026, 10, 1), date(2026, 11, 2)
            )
            first = week_service.create_week(date(2026, 10, 25))
            second = week_service.create_week(date(2026, 11, 1))
            self.assertEqual(slot_service.get_slot(first, 5, "morning").assignee, "Friday only")
            self.assertIsNone(slot_service.get_slot(second, 6, "morning").assignee)

    def test_concurrent_first_visits_share_one_complete_week(self):
        target = date(2026, 11, 8)
        barrier = Barrier(2)
        original = week_service.get_week

        def lookup(start):
            result = original(start)
            if result is None:
                barrier.wait(timeout=10)
            return result

        def visit(_):
            with self.app.test_client() as client:
                return client.get("/?week=" + target.isoformat()).status_code

        with patch.object(week_service, "get_week", lookup), patch.object(
            week_service, "is_creatable", return_value=True
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(list(pool.map(visit, range(2))), [200, 200])
        with self.app.app_context():
            self.assertEqual(Week.query.count(), 1)
            self.assertEqual(Slot.query.count(), 14)

    def test_redirect_validator_rejects_external_and_ambiguous_urls(self):
        with self.app.test_request_context():
            for target in [None, "https://evil.example", "//evil.example", "/\\evil.example", "/\n/evil.example", "javascript:alert(1)"]:
                with self.subTest(target=target):
                    self.assertEqual(local_redirect_target(target), "/")
            self.assertEqual(local_redirect_target("/?week=2026-11-01"), "/?week=2026-11-01")

    def test_all_redirect_routes_reject_external_next(self):
        with self.app.test_client() as client:
            response = client.post("/auth/login", data={"password": "test-password", "next": "https://evil.example"})
            self.assertEqual(response.headers["Location"], "/")
            response = client.post("/api/recurring", data={"day_index": "0", "shift": "morning", "next": "//evil.example"})
            self.assertEqual(response.headers["Location"], "/")
            response = client.post("/auth/logout", data={"next": "https://evil.example"})
            self.assertEqual(response.headers["Location"], "/")

    def test_login_preserves_local_week_destination(self):
        with self.app.test_client() as client:
            destination = "/?week=2026-11-01"
            response = client.post("/auth/login", data={"password": "test-password", "next": destination})
            self.assertEqual(response.headers["Location"], destination)


if __name__ == "__main__":
    unittest.main()
