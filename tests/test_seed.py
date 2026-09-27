import unittest

from db_seeder import DefaultConferenceSeeder

class DefaultConferenceSeederTest(unittest.TestCase):
    def test_default_conferences_include_two_open_and_one_restricted(self):
        conferences = DefaultConferenceSeeder.default_conferences()
        registration_types = [
            conference["registration_type"] for conference in conferences
        ]

        self.assertEqual(len(conferences), 3)
        self.assertEqual(registration_types.count("open"), 2)
        self.assertEqual(registration_types.count("restricted"), 1)


if __name__ == "__main__":
    unittest.main()
