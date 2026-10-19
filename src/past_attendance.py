# Purpose: Retrieve a participant's past conference attendance.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft this code.

from db import CONFERENCE_TABLE, PARTICIPANT_CONFERENCE_TABLE, get_connection


def get_past_events(participant_id):
    """Treat registration at the event time as attendance."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT c.conference_id, c.name,
                       c.event_datetime, c.location
                FROM `{CONFERENCE_TABLE}` c
                JOIN `{PARTICIPANT_CONFERENCE_TABLE}` pc
                    ON pc.conference_id = c.conference_id
                WHERE pc.participant_id = %s
                  AND pc.status = %s
                  AND pc.registered_at <= c.event_datetime
                  AND c.event_datetime < CURRENT_TIMESTAMP
                ORDER BY c.event_datetime DESC, c.conference_id""",
            (participant_id, "registered"),
        )
        return [
            {
                "conference_id": row[0],
                "name": row[1],
                "event_datetime": row[2],
                "location": row[3],
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        connection.close()
