import csv
import io
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.append("../src")

from app import app
from conference import ConferenceModel
from user import UserModel


class ParticipantCsvExportTest(unittest.TestCase):
    """Tests the participant CSV download route."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.get_conference_participants")
    @patch("app.get_conference_for_organizer")
    @patch("app.get_user_by_id")
    def test_organizer_downloads_participant_csv(
        self,
        get_user_by_id,
        get_conference_for_organizer,
        get_conference_participants,
    ):
        get_user_by_id.return_value = UserModel(
            "org1", "Organizer", "Organizer", "organizer@example.edu",
            False, False, True,
        )
        get_conference_for_organizer.return_value = ConferenceModel(
            "conference-1",
            "org1",
            "Example Conference",
            "Conference description",
            datetime(2026, 10, 4, 12, 0),
            "Room 101",
            "open",
            True,
            None,
            None,
        )
        get_conference_participants.return_value = [
            (
                "p1",
                "Ada",
                "Lovelace",
                "ada@example.edu",
                "registered",
                datetime(2026, 9, 1, 10, 0),
                datetime(2026, 9, 2, 11, 0),
            )
        ]

        with self.client.session_transaction() as session:
            session["user_id"] = "org1"

        response = self.client.get("/conferences/conference-1/participants.csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertEqual(
            response.headers["Content-Disposition"],
            'attachment; filename="participants-conference-1.csv"',
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")

        rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(
            rows,
            [
                [
                    "participant_id",
                    "first_name",
                    "last_name",
                    "email",
                    "status",
                    "invited_at",
                    "registered_at",
                ],
                [
                    "p1",
                    "Ada",
                    "Lovelace",
                    "ada@example.edu",
                    "registered",
                    "2026-09-01 10:00:00",
                    "2026-09-02 11:00:00",
                ],
            ],
        )
        get_conference_for_organizer.assert_called_once_with(
            "conference-1", "org1"
        )
        get_conference_participants.assert_called_once_with("conference-1")


if __name__ == "__main__":
    unittest.main()
