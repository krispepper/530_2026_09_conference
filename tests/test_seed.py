import unittest
from unittest.mock import patch

from db_seeder import DBSeeder

class DefaultConferenceSeederTest(unittest.TestCase):
    """Tests the default users and conferences used for demo initialization."""

    def test_default_users_include_organizer_and_admin(self):
        """Verifies the seeded users have the expected roles."""
        users = DBSeeder.default_users()

        self.assertEqual(
            {user["user_id"] for user in users},
            {"u1", "u2", "u3", "u4"},
        )
        organizer = next(user for user in users if user["user_id"] == "u1")
        admin = next(user for user in users if user["user_id"] == "u2")
        self.assertTrue(organizer["is_organizer"])
        self.assertFalse(organizer["is_admin"])
        self.assertTrue(admin["is_admin"])
        self.assertFalse(admin["is_organizer"])
        participant = next(user for user in users if user["user_id"] == "u3")
        self.assertTrue(participant["is_participant"])
        self.assertFalse(participant["is_admin"])
        self.assertFalse(participant["is_organizer"])
        invited_participant = next(
            user for user in users if user["user_id"] == "u4"
        )
        self.assertTrue(invited_participant["is_participant"])
        self.assertFalse(invited_participant["is_admin"])
        self.assertFalse(invited_participant["is_organizer"])

    def test_default_conferences_include_two_open_and_one_restricted(self):
        """Verifies the demo data includes two open and one restricted conference."""
        conferences = DBSeeder.default_conferences()
        registration_types = [
            conference["registration_type"] for conference in conferences
        ]

        self.assertEqual(len(conferences), 3)
        self.assertEqual(registration_types.count("open"), 2)
        self.assertEqual(registration_types.count("restricted"), 1)

    def test_default_conferences_are_assigned_to_both_seeded_users(self):
        """
        Verifies default conferences are assigned to both seeded organizers.
        Admin access allows u2 to manage the seeded conference set.
        """
        conferences = DBSeeder.default_conferences()
        owners = [conference["organizer_id"] for conference in conferences]

        self.assertIn("u1", owners)
        self.assertIn("u2", owners)
        self.assertGreaterEqual(owners.count("u1"), 2)

    @patch("conference.get_connection")
    @patch("db_seeder.invite_participant")
    @patch("db_seeder.get_connection")
    def test_u4_sees_invited_restricted_conference(
        self,
        get_seed_connection,
        invite_participant,
        get_conference_connection,
    ):
        """Verifies an invited u4 sees the restricted conference in their list."""
        seed_connection = get_seed_connection.return_value
        seed_cursor = seed_connection.cursor.return_value
        conference_connection = get_conference_connection.return_value
        conference_cursor = conference_connection.cursor.return_value
        conference_cursor.fetchall.return_value = [
            (
                "c3",
                "u1",
                "Invited Leadership Workshop",
                "A restricted workshop for invited participants.",
                None,
                "Graduate Studies Room",
                "restricted",
                True,
                None,
                None,
                "invited",
            )
        ]

        DBSeeder.initialize_db()

        from conference import get_my_conferences

        conferences = get_my_conferences("u4")

        self.assertTrue(invite_participant.called)
        self.assertEqual(len(conferences), 1)
        self.assertEqual(conferences[0].conference_id, "c3")
        self.assertEqual(conferences[0].registration_type, "restricted")
        self.assertEqual(conferences[0].membership_status, "Invited")
        conference_cursor.close.assert_called_once()
        conference_connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
