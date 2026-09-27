from datetime import datetime

from db import CONFERENCE_TABLE, USER_TABLE, get_connection


class DefaultConferenceSeeder:
    """Creates sample conferences for a newly initialized database."""

    ORGANIZER_ID = "u777" # Unique ID for the default organizer user

    @classmethod
    def default_conferences(cls):
        return [
            {
                "name": "Adelphi Software Engineering Conference",
                "description": "An open conference for software engineering students.",
                "event_datetime": datetime(2027, 4, 10, 9, 0),
                "location": "University Conference Center",
                "registration_type": "open",
            },
            {
                "name": "Spring Technology Research Forum",
                "description": "An open forum for technology research presentations.",
                "event_datetime": datetime(2027, 5, 15, 10, 0),
                "location": "Science Building Auditorium",
                "registration_type": "open",
            },
            {
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
            if cursor.fetchone()[0] != 0:
                return

            cursor.execute(
                f"""INSERT IGNORE INTO `{USER_TABLE}`
                    (user_id, f_name, l_name, email, is_admin,
                     is_participant, is_organizer)
                    VALUES (%s, %s, %s, %s, TRUE, FALSE, TRUE)""",
                (
                    cls.ORGANIZER_ID,
                    "Default",
                    "Organizer",
                    "seed-organizer@example.edu",
                ),
            )
            sql = f"""INSERT INTO `{CONFERENCE_TABLE}`
                (organizer_id, name, description, event_datetime, location,
                 registration_type, is_published, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)"""
            for conference in cls.default_conferences():
                cursor.execute(
                    sql,
                    (
                        cls.ORGANIZER_ID,
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
