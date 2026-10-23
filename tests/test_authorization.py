import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import app as app_module
from conference import ConferenceModel
from user import UserModel


def make_user(user_id, *, is_admin=False, is_organizer=False, is_participant=False):
    return UserModel(
        user_id,
        "Test",
        "User",
        f"{user_id}@example.edu",
        is_participant,
        is_admin,
        is_organizer,
    )


def make_conference(conference_id="conference-1", organizer_id="u1"):
    return ConferenceModel(
        conference_id,
        organizer_id,
        "Test Conference",
        "A conference used by endpoint authorization tests.",
        None,
        "Test location",
        "open",
        True,
        None,
        None,
    )


class AuthorizationEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(
            TESTING=True,
            SECRET_KEY="authorization-test-secret",
        )
        cls.client = app_module.app.test_client()

    def sign_in(self, user):
        with self.client.session_transaction() as session:
            session["user_id"] = user.user_id

    def tearDown(self):
        with self.client.session_transaction() as session:
            session.clear()

    @patch("app.get_user_by_id")
    def test_unauthenticated_create_conference_is_rejected(self, get_user):
        response = self.client.get("/conferences/new")

        self.assertEqual(response.status_code, 403)
        get_user.assert_not_called()

    @patch("app.get_user_by_id")
    def test_participant_cannot_create_conference(self, get_user):
        participant = make_user("u3", is_participant=True)
        get_user.return_value = participant
        self.sign_in(participant)

        response = self.client.get("/conferences/new")

        self.assertEqual(response.status_code, 403)

    @patch("app.get_user_by_id")
    def test_admin_can_create_conference(self, get_user):
        admin = make_user("u2", is_admin=True)
        get_user.return_value = admin
        self.sign_in(admin)

        response = self.client.get("/conferences/new")

        self.assertEqual(response.status_code, 200)

    @patch("app.get_user_by_id")
    def test_organizer_cannot_manage_users(self, get_user):
        organizer = make_user("u1", is_organizer=True)
        get_user.return_value = organizer
        self.sign_in(organizer)

        response = self.client.get("/add_user")

        self.assertEqual(response.status_code, 403)

    @patch("app.get_conference_for_admin")
    @patch("app.get_user_by_id")
    @patch("app.get_conference_by_id")
    def test_existing_inaccessible_conference_returns_forbidden(
        self,
        get_conference_by_id,
        get_user_by_id,
        get_conference_for_admin,
    ):
        participant = make_user("u3", is_participant=True)
        get_user_by_id.return_value = participant
        get_conference_by_id.return_value = None
        get_conference_for_admin.return_value = make_conference()
        self.sign_in(participant)

        response = self.client.get("/conferences/conference-1")

        self.assertEqual(response.status_code, 403)
        self.assertIn(b"permission", response.data)

    @patch("app.get_conference_for_admin")
    @patch("app.get_user_by_id")
    @patch("app.get_conference_by_id")
    def test_missing_conference_returns_not_found(
        self,
        get_conference_by_id,
        get_user_by_id,
        get_conference_for_admin,
    ):
        participant = make_user("u3", is_participant=True)
        get_user_by_id.return_value = participant
        get_conference_by_id.return_value = None
        get_conference_for_admin.return_value = None
        self.sign_in(participant)

        response = self.client.get("/conferences/missing")

        self.assertEqual(response.status_code, 404)

    @patch("app.get_conference_for_admin")
    @patch("app.get_user_by_id")
    @patch("app.get_conference_by_id")
    def test_unauthenticated_existing_inaccessible_conference_requires_login(
        self,
        get_conference_by_id,
        get_user_by_id,
        get_conference_for_admin,
    ):
        get_conference_by_id.return_value = None
        get_conference_for_admin.return_value = make_conference()

        response = self.client.get("/conferences/conference-1")

        self.assertEqual(response.status_code, 401)

    @patch("app.cancel_registration")
    @patch("app.get_user_by_id")
    def test_participant_cannot_cancel_another_users_registration(
        self,
        get_user_by_id,
        cancel_registration,
    ):
        participant = make_user("u3", is_participant=True)
        get_user_by_id.return_value = participant
        self.sign_in(participant)

        response = self.client.delete("/cancel_registration/conference-1/u4")

        self.assertEqual(response.status_code, 403)
        cancel_registration.assert_not_called()


if __name__ == "__main__":
    unittest.main()
