import unittest
from unittest.mock import MagicMock, patch
from user import delete_user_by_id

class TestDeleteUser(unittest.TestCase):

    @patch('user.get_connection')
    def test_delete_user_by_id_success(self, mock_get_conn):
        # Mock DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Call your delete function
        delete_user_by_id(123)

        # Verify delete was called correctly
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
        print("test_delete_user_by_id_success PASSED")

    @patch('user.get_connection')
    def test_delete_sql_contains_delete(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        delete_user_by_id(999)

        # Get the SQL that was executed
        sql_query = mock_cursor.execute.call_args[0][0]
        self.assertIn("DELETE", sql_query.upper())
        print(f"SQL verified: {sql_query}")

if __name__ == '__main__':
    unittest.main()