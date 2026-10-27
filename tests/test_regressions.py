import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import Slot, Week
from app.security import local_redirect_target
from app.services import recurring_service, slot_service, week_service
from config import Config


class GroupClient(FlaskClient):
    def open(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            parsed = urlsplit(args[0])
            query = parse_qsl(parsed.query, keep_blank_values=True)
            query.append(("groupId", "test-group"))
            args = (urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)), *args[1:])
        return super().open(*args, **kwargs)


class RegressionTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.path = Path(handle.name)
        handle.close()

        class TestConfig(Config):
            TESTING = True
            GROUP_ID = "test-group"
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
        self.app.test_client_class = GroupClient
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
            self.assertEqual(response.headers["Location"], "/?groupId=test-group")
            response = client.post("/api/recurring", data={"day_index": "0", "shift": "morning", "next": "//evil.example"})
            self.assertEqual(response.headers["Location"], "/?groupId=test-group")
            response = client.post("/auth/logout", data={"next": "https://evil.example"})
            self.assertEqual(response.headers["Location"], "/?groupId=test-group")

    def test_login_preserves_local_week_destination(self):
        with self.app.test_client() as client:
            destination = "/?week=2026-11-01"
            response = client.post("/auth/login", data={"password": "test-password", "next": destination})
            self.assertEqual(response.headers["Location"], destination + "&groupId=test-group")

    def test_group_required_on_all_http_and_socket_transport_requests(self):
        client = FlaskClient(self.app)
        for path in ["/", "/auth/login", "/api/slot", "/static/css/main.css", "/socket.io/?EIO=4&transport=polling"]:
            for group in ["", "groupId=wrong", "groupId=test-group&groupId=wrong"]:
                separator = "&" if "?" in path else "?"
                with self.subTest(path=path, group=group):
                    self.assertEqual(client.get(path + separator + group).status_code, 403)
        self.assertEqual(client.post("/api/slot", data={"groupId": "test-group"}).status_code, 403)
        with client.get("/static/css/main.css?groupId=test-group") as response:
            self.assertEqual(response.status_code, 200)
        response = client.get("/socket.io/?EIO=4&transport=polling&groupId=test-group")
        self.assertEqual(response.status_code, 200)

    def test_missing_group_configuration_denies_access(self):
        self.app.config["GROUP_ID"] = ""
        self.assertEqual(FlaskClient(self.app).get("/?groupId=test-group").status_code, 403)

    def test_authorized_page_preserves_group_without_granting_edit_access(self):
        client = FlaskClient(self.app)
        response = client.get("/?groupId=test-group")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("/static/css/main.css?groupId=test-group", html)
        self.assertIn("groupId=test-group", html)
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(client.post("/api/slot?groupId=test-group").status_code, 403)


if __name__ == "__main__":
    unittest.main()
