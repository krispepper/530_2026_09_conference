
# Unit test written by Priya Vaghela.
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from user import UserModel
from user import get_user_by_id

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))



class TestGetUserById(unittest.TestCase):
    @patch("user.get_connection")
    def test_returns_none_when_user_does_not_exist(self, mock_get_connection):
        connection = MagicMock()
        connection.cursor.return_value.fetchone.return_value = None
        mock_get_connection.return_value = connection

        result = get_user_by_id(9999)

        self.assertIsNone(result)

sys.path.append('../src')

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
