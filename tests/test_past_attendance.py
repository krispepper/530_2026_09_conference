# Purpose: Test participant access and the past events page.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft these tests.

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import app


class PastEventsPageTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-only-key")
        self.client = app.test_client()
        self.participant = SimpleNamespace(
            user_id="u3", is_participant=True,
            is_admin=False, is_organizer=False,
        )

    def sign_in(self):
        with self.client.session_transaction() as session:
            session["user_id"] = "u3"

    @patch("app.get_past_events")
    def test_login_required(self, history):
        response = self.client.get("/my-conferences/past")
        self.assertEqual(response.status_code, 401)
        history.assert_not_called()

    @patch("app.get_past_events")
    @patch("app.get_user_by_id")
    def test_nonparticipant_is_blocked(self, user_lookup, history):
        self.sign_in()
        user_lookup.return_value = SimpleNamespace(is_participant=False)
        response = self.client.get("/my-conferences/past")
        self.assertEqual(response.status_code, 403)
        history.assert_not_called()

    @patch("app.get_past_events")
    @patch("app.get_user_by_id")
    def test_empty_history_message(self, user_lookup, history):
        self.sign_in()
        user_lookup.return_value = self.participant
        history.return_value = []
        response = self.client.get("/my-conferences/past")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"You have not attended any past events.", response.data
        )

    @patch("app.get_past_events")
    @patch("app.get_user_by_id")
    def test_event_details_are_displayed(self, user_lookup, history):
        self.sign_in()
        user_lookup.return_value = self.participant
        history.return_value = [{
            "conference_id": "past1",
            "name": "Past Test Conference",
            "event_datetime": "2026-09-01 10:00:00",
            "location": "Test Hall",
        }]
        response = self.client.get("/my-conferences/past")
        self.assertEqual(response.status_code, 200)
        for expected in [
            b"Past Test Conference", b"2026-09-01 10:00:00", b"Test Hall"
        ]:
            self.assertIn(expected, response.data)

    @patch("app.get_past_events")
    @patch("app.get_user_by_id")
    def test_history_uses_signed_in_user(self, user_lookup, history):
        self.sign_in()
        user_lookup.return_value = self.participant
        history.return_value = []
        self.client.get("/my-conferences/past?participant_id=u4")
        history.assert_called_once_with("u3")


if __name__ == "__main__":
    unittest.main()
