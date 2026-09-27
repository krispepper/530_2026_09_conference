from datetime import datetime

from db import CONFERENCE_TABLE, USER_TABLE, get_connection


class DefaultConferenceSeeder:
    """Creates sample conferences for a newly initialized database."""

    ORGANIZER_ID = "u1"
    ADMIN_ID = "u2"

    @classmethod
    def default_users(cls):
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
        ]

    @classmethod
    def default_conferences(cls):
        return [
            {
                "organizer_id": cls.ORGANIZER_ID,
                "name": "Adelphi Software Engineering Conference",
                "description": "An open conference for software engineering students.",
                "event_datetime": datetime(2027, 4, 10, 9, 0),
                "location": "University Conference Center",
                "registration_type": "open",
            },
            {
                "organizer_id": cls.ADMIN_ID,
                "name": "Spring Technology Research Forum",
                "description": "An open forum for technology research presentations.",
                "event_datetime": datetime(2027, 5, 15, 10, 0),
                "location": "Science Building Auditorium",
                "registration_type": "open",
            },
            {
                "organizer_id": cls.ORGANIZER_ID,
                "name": "Invited Leadership Workshop",
                "description": "A restricted workshop for invited participants.",
                "event_datetime": datetime(2027, 6, 5, 13, 0),
                "location": "Graduate Studies Room",
                "registration_type": "restricted",
            },
        ]

    @classmethod
    def seed_if_empty(cls):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{CONFERENCE_TABLE}`")
            conference_count = cursor.fetchone()[0]

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
            if conference_count != 0:
                connection.commit()
                return

            sql = f"""INSERT INTO `{CONFERENCE_TABLE}`
                (organizer_id, name, description, event_datetime, location,
                 registration_type, is_published, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)"""
            for conference in cls.default_conferences():
                cursor.execute(
                    sql,
                    (
                        conference["organizer_id"],
                        conference["name"],
                        conference["description"],
                        conference["event_datetime"],
                        conference["location"],
                        conference["registration_type"],
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
