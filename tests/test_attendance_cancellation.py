# Purpose: Test cancellation rules that preserve attendance history.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft these tests.

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from participant_conf import unregister_participant


class AttendanceCancellationTests(unittest.TestCase):
    @patch("participant_conf.get_connection")
    def test_past_event_cannot_be_canceled(self, get_connection):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        get_connection.return_value = connection
        cursor.fetchone.return_value = (0,)

        with self.assertRaisesRegex(ValueError, "already|started"):
            unregister_participant("u3", "past1")

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any("DELETE" in sql.upper() for sql in statements))
        connection.commit.assert_not_called()
        connection.rollback.assert_called_once()

    @patch("participant_conf.log_conference_action")
    @patch("participant_conf.get_connection")
    def test_future_event_can_be_canceled(self, get_connection, log_action):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        get_connection.return_value = connection
        cursor.fetchone.return_value = (1,)
        cursor.rowcount = 1

        with patch(
            "waiting_list.promote_next_waiting_participant"
        ) as promote:
            unregister_participant("u3", "future1")

        promote.assert_called_once_with(cursor, "future1")
        connection.commit.assert_called_once()
        log_action.assert_called_once_with("future1", "u3", "UNREGISTER")


if __name__ == "__main__":
    unittest.main()
