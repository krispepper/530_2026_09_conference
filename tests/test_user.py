import unittest

import sys
sys.path.append('../src')

from user import UserModel

class DefaultUserModelTest(unittest.TestCase):
    def test_user_model_class(self):
        # Test by Ned Hunter
        test_model = UserModel("test_user", "John", "Doe", "foobar@lorem.ipsum", True, False, False)

        self.assertEqual(test_model.user_id, "test_user")
        self.assertEqual(test_model.f_name, "John")
        self.assertEqual(test_model.l_name, "Doe")
        self.assertEqual(test_model.email, "foobar@lorem.ipsum")
        self.assertTrue(test_model.is_participant)
        self.assertFalse(test_model.is_admin)
        self.assertFalse(test_model.is_organizer)

if __name__ == "__main__":
    unittest.main()

    