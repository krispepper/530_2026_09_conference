from datetime import datetime

from db import CONFERENCE_TABLE, USER_TABLE, get_connection
from participant_conf import invite_participant


class DBSeeder:
    """Creates sample conferences and users for a newly initialized database."""

    ORGANIZER_ID = "u1"
    ADMIN_ID = "u2"
    PARTICIPANT_ID = "u3"
    PARTICIPANT_ID_2 = "u4"

    @classmethod
    def default_users(cls):
        """
        Builds the default users used for a newly initialized database.
        @return: list of user dictionaries
        """
        return [
            {
                "user_id": cls.ORGANIZER_ID,
                "f_name": "The",
                "l_name": "Organizer",
                "email": "organizer@example.edu",
                "is_admin": False,
                "is_participant": False,
                "is_organizer": True,
            },
            {
                "user_id": cls.ADMIN_ID,
                "f_name": "Dev",
                "l_name": "Admin",
                "email": "dev@example.edu",
                "is_admin": True,
                "is_participant": False,
                "is_organizer": False,
            },
            {
                "user_id": cls.PARTICIPANT_ID,
                "f_name": "Conference",
                "l_name": "Participant",
                "email": "participant@example.edu",
                "is_admin": False,
                "is_participant": True,
                "is_organizer": False,
            },
            {
                "user_id": cls.PARTICIPANT_ID_2,
                "f_name": "Conference",
                "l_name": "Participant 2",
                "email": "invited@example.edu",
                "is_admin": False,
                "is_participant": True,
                "is_organizer": False,
            },
        ]

    @classmethod
    def default_conferences(cls):
        """
        Builds the default conferences used for a newly initialized database.
        @return: list of conference dictionaries
        """
        return [
            {
                "conference_id": "c1",
                "organizer_id": cls.ORGANIZER_ID,
                "name": "Adelphi Software Engineering Conference",
                "description": "An open conference for software engineering students.",
                "event_datetime": datetime(2027, 4, 10, 9, 0),
                "location": "University Conference Center",
                "registration_type": "open",
            },
            {
                "conference_id": "c2",
                "organizer_id": cls.ADMIN_ID,
                "name": "Spring Technology Research Forum",
                "description": "An open forum for technology research presentations.",
                "event_datetime": datetime(2027, 5, 15, 10, 0),
                "location": "Science Building Auditorium",
                "registration_type": "open",
            },
            {
                "conference_id": "c3",
                "organizer_id": cls.ORGANIZER_ID,
                "name": "Invited Leadership Workshop",
                "description": "A restricted workshop for invited participants.",
                "event_datetime": datetime(2027, 6, 5, 13, 0),
                "location": "Graduate Studies Room",
                "registration_type": "restricted",
            },
        ]

    @classmethod
    def seed_users(cls, cursor):
        """
        Inserts the default users.
        @param cursor: active database cursor
        """
        user_sql = f"""INSERT IGNORE INTO `{USER_TABLE}`
            (user_id, f_name, l_name, email, is_admin,
             is_participant, is_organizer)
            VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        for user in cls.default_users():
            cursor.execute(
                user_sql,
                (
                    user["user_id"],
                    user["f_name"],
                    user["l_name"],
                    user["email"],
                    user["is_admin"],
                    user["is_participant"],
                    user["is_organizer"],
                ),
            )

    @classmethod
    def seed_conferences(cls, cursor):
        """
        Inserts the default conferences.
        @param cursor: active database cursor
        """
        conference_sql = f"""INSERT INTO `{CONFERENCE_TABLE}`
            (conference_id, organizer_id, name, description, event_datetime, location,
             registration_type, is_published, published_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)"""
        for conference in cls.default_conferences():
            cursor.execute(
                conference_sql,
                (
                    conference["conference_id"],
                    conference["organizer_id"],
                    conference["name"],
                    conference["description"],
                    conference["event_datetime"],
                    conference["location"],
                    conference["registration_type"],
                ),
            )

    @classmethod
    def initialize_db(cls):
        """
        Creates the default users and conferences, then seeds the demo DB.
        """
        connection = get_connection()
        cursor = connection.cursor()

        try:
            cls.seed_users(cursor)
            cls.seed_conferences(cursor)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        # Invite the second participant to the restricted conference
        restricted_conference = next(
            (
                conference
                for conference in cls.default_conferences()
                if conference["registration_type"] == "restricted"
            ),
            None,
        )
        if restricted_conference is not None:
            invite_participant(
                participant_id=cls.PARTICIPANT_ID_2,
                conference_id=restricted_conference["conference_id"],
                organizer_id=restricted_conference["organizer_id"],
            )