import unittest

from db_seeder import DefaultConferenceSeeder

class DefaultConferenceSeederTest(unittest.TestCase):
    # Author: Conference team - unit test assignment.
    def test_default_users_include_organizer_and_admin(self):
        users = DefaultConferenceSeeder.default_users()

        self.assertEqual(
            {user["user_id"] for user in users},
            {"u1", "u2", "u3"},
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

    def test_default_conferences_include_two_open_and_one_restricted(self):
        conferences = DefaultConferenceSeeder.default_conferences()
        registration_types = [
            conference["registration_type"] for conference in conferences
        ]

        self.assertEqual(len(conferences), 3)
        self.assertEqual(registration_types.count("open"), 2)
        self.assertEqual(registration_types.count("restricted"), 1)

    # The first and third conferences are shared through u1's organizer access;
    # u2's admin access can manage the same seeded conference set.
    def test_default_conferences_are_assigned_to_both_seeded_users(self):
        conferences = DefaultConferenceSeeder.default_conferences()
        owners = [conference["organizer_id"] for conference in conferences]

        self.assertIn("u1", owners)
        self.assertIn("u2", owners)
        self.assertGreaterEqual(owners.count("u1"), 2)


if __name__ == "__main__":
    unittest.main()
