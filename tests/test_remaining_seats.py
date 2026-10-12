# Purpose: Test seat calculations and registration capacity rules.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft these tests.

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seats import calculate_remaining_seats
from participant_conf import register_participant


class RemainingSeatsTests(unittest.TestCase):
    def test_available_seats(self):
        self.assertEqual(calculate_remaining_seats(20, 12), 8)

    def test_full_conference(self):
        self.assertEqual(calculate_remaining_seats(20, 20), 0)

    def test_over_capacity_displays_zero(self):
        self.assertEqual(calculate_remaining_seats(20, 25), 0)

    def test_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_remaining_seats(20, -1)

    @patch("participant_conf.get_connection")
    def test_registration_is_blocked_when_full(self, mock_connection):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        mock_connection.return_value = connection
        cursor.fetchone.side_effect = [
            ("open", True, 1),
            ("u3",),
            None,
        ]
        cursor.fetchall.return_value = [("u4",)]

        with self.assertRaisesRegex(ValueError, "full"):
            register_participant("u3", "c1")

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()

    @patch("participant_conf.get_connection")
    def test_registration_succeeds_when_seat_available(self, mock_connection):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        mock_connection.return_value = connection
        cursor.fetchone.side_effect = [
            ("open", True, 2),
            ("u3",),
            None,
        ]
        cursor.fetchall.return_value = [("u4",)]

        register_participant("u3", "c1")

        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()

    @patch("participant_conf.get_connection")
    def test_duplicate_registration_does_not_insert_again(self, mock_connection):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        mock_connection.return_value = connection
        cursor.fetchone.side_effect = [
            ("open", True, 1),
            ("u3",),
            ("registered",),
        ]

        register_participant("u3", "c1")

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any("INSERT" in sql.upper() for sql in statements))


if __name__ == "__main__":
    unittest.main()
