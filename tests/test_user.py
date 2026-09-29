# Unit test written by Priya Vaghela.
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from user import get_user_by_id


class TestGetUserById(unittest.TestCase):
    @patch("user.get_connection")
    def test_returns_none_when_user_does_not_exist(self, mock_get_connection):
        connection = MagicMock()
        connection.cursor.return_value.fetchone.return_value = None
        mock_get_connection.return_value = connection

        result = get_user_by_id(9999)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()