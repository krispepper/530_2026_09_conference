# Purpose: Test waiting-list rules and automatic promotion.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft these tests.

import unittest
from unittest.mock import MagicMock, patch

from waiting_list import (
    join_waiting_list,
    leave_waiting_list,
    promote_next_waiting_participant,
)


class WaitingListTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.rowcount = 1
        patcher = patch(
            "waiting_list.get_connection",
            return_value=self.connection,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def prepare_join(
        self, *, registration_type="open", status=None,
        queued=False, registration_open=True, registered_count=1
    ):
        self.cursor.fetchone.side_effect = [
            (registration_type, 1, True, True, registration_open),
            (True, False),
            ("organizer1",),
            (status,) if status else None,
            (10,) if queued else None,
        ]
        self.cursor.fetchall.return_value = [
            (f"registered{i}",) for i in range(registered_count)
        ]

    def statements(self):
        return [
            call.args[0].strip()
            for call in self.cursor.execute.call_args_list
        ]

    def test_join_full_conference(self):
        self.prepare_join()
        result = join_waiting_list("u3", "c1")
        self.assertEqual(result, "You have joined the waiting list.")
        self.assertTrue(any(
            sql.startswith("INSERT INTO `conference_waiting_list`")
            for sql in self.statements()
        ))
        self.connection.commit.assert_called_once()

    def test_duplicate_does_not_insert(self):
        self.prepare_join(queued=True)
        result = join_waiting_list("u3", "c1")
        self.assertEqual(result, "You are already on the waiting list.")
        self.assertFalse(any(
            sql.startswith("INSERT") for sql in self.statements()
        ))

    def test_registered_participant_cannot_join(self):
        self.prepare_join(status="registered")
        with self.assertRaisesRegex(ValueError, "already registered"):
            join_waiting_list("u3", "c1")
        self.connection.rollback.assert_called_once()

    def test_restricted_conference_requires_invitation(self):
        self.prepare_join(registration_type="restricted")
        with self.assertRaises(PermissionError):
            join_waiting_list("u3", "c1")

    def test_invited_participant_can_join_restricted_queue(self):
        self.prepare_join(
            registration_type="restricted", status="invited"
        )
        self.assertEqual(
            join_waiting_list("u3", "c1"),
            "You have joined the waiting list.",
        )
        self.assertFalse(any(
            sql.startswith("UPDATE `participant_conf`")
            for sql in self.statements()
        ))

    def test_closed_registration_blocks_join(self):
        self.prepare_join(registration_open=False)
        with self.assertRaisesRegex(ValueError, "closed"):
            join_waiting_list("u3", "c1")

    def test_available_seat_blocks_waiting_list_join(self):
        self.prepare_join(registered_count=0)
        with self.assertRaisesRegex(ValueError, "Seats are available"):
            join_waiting_list("u3", "c1")

    def test_leave_removes_only_own_entry(self):
        self.cursor.fetchone.return_value = (
            "open", 1, True, True, True
        )
        self.assertEqual(
            leave_waiting_list("u3", "c1"),
            "You have left the waiting list.",
        )
        self.assertEqual(
            self.cursor.execute.call_args.args[1], ("u3", "c1")
        )
        self.connection.commit.assert_called_once()

    def test_first_eligible_participant_is_promoted(self):
        self.cursor.fetchone.side_effect = [
            ("open", 1, True, True, True),
            (True, False),
            None,
        ]
        self.cursor.fetchall.side_effect = [
            [],
            [(10, "u3"), (11, "u4")],
        ]

        result = promote_next_waiting_participant(self.cursor, "c1")

        self.assertEqual(result, "u3")
        insert = next(
            call for call in self.cursor.execute.call_args_list
            if call.args[0].strip().startswith(
                "INSERT INTO `participant_conf`"
            )
        )
        self.assertEqual(insert.args[1][:2], ("u3", "c1"))
        self.assertEqual(
            self.cursor.execute.call_args.args[1], (10,)
        )
        # Cancellation owns the transaction; promotion must not commit.
        self.connection.commit.assert_not_called()

    def test_closed_registration_blocks_promotion(self):
        self.cursor.fetchone.return_value = (
            "open", 1, True, True, False
        )
        self.assertIsNone(
            promote_next_waiting_participant(self.cursor, "c1")
        )
        self.assertFalse(any(
            sql.startswith(("INSERT", "UPDATE", "DELETE"))
            for sql in self.statements()
        ))

    def test_full_conference_blocks_promotion(self):
        self.cursor.fetchone.return_value = (
            "open", 1, True, True, True
        )
        self.cursor.fetchall.return_value = [("u4",)]
        self.assertIsNone(
            promote_next_waiting_participant(self.cursor, "c1")
        )
        self.assertFalse(any(
            sql.startswith(("INSERT", "UPDATE", "DELETE"))
            for sql in self.statements()
        ))


if __name__ == "__main__":
    unittest.main()
