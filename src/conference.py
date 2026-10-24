# Purpose: Create, retrieve, and validate conferences.
# AI assistance: ChatGPT helped add capacity validation and storage.
from datetime import datetime
from uuid import uuid4

from db import CONFERENCE_TABLE, PARTICIPANT_CONFERENCE_TABLE, get_connection
from participant_conf import ParticipantConferenceStatus
from audit_log import log_conference_action

VALID_REGISTRATION_TYPES = {"open", "restricted"}

class ConferenceModel:
    def __init__(
        self,
        conference_id,
        organizer_id,
        name,
        description,
        event_datetime,
        location,
        registration_type,
        is_published,
        created_at,
        published_at,
        registration_deadline=None,
    ):
        self.conference_id = conference_id
        self.organizer_id = organizer_id
        self.name = name
        self.description = description
        self.event_datetime = event_datetime
        self.location = location
        self.registration_type = registration_type
        self.is_published = is_published
        self.created_at = created_at
        self.published_at = published_at
        self.registration_deadline = registration_deadline

def create_conference(
    organizer_id,
    name,
    description,
    event_datetime,
    location,
    registration_type,
    capacity,
    registration_deadline,
):
    """
    Creates conference in the database.
    @return: conference_id
    """
    connection = get_connection()
    cursor = connection.cursor()

    sql = f"""INSERT INTO `{CONFERENCE_TABLE}`
        (conference_id, organizer_id, name, description, event_datetime, location,
         registration_type, capacity, registration_deadline, is_published, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, NULL)"""
    try:
        conference_id = str(uuid4())
        cursor.execute(sql, (
            conference_id, organizer_id, name, description, event_datetime,
            location, registration_type, capacity, registration_deadline,
        ))
        connection.commit()
        log_conference_action(conference_id, organizer_id, "CREATE")
        return conference_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

def get_conference_by_id(conference_id, participant_id=None, is_published=True):
    connection = get_connection()
    cursor = connection.cursor()

    sql = f"""SELECT c.conference_id, c.organizer_id, c.name, c.description,
    c.event_datetime, c.location, c.registration_type, c.is_published,
    c.created_at, c.published_at, c.registration_deadline
        FROM `{CONFERENCE_TABLE}` c
        LEFT JOIN `{PARTICIPANT_CONFERENCE_TABLE}` pc
            ON pc.conference_id = c.conference_id
            AND pc.participant_id = %s
        WHERE c.conference_id = %s
        AND c.is_published = {is_published}
        AND (
            c.registration_type = 'open'
            OR pc.status IN (%s, %s, %s)
        )"""
    try:
        cursor.execute(
            sql,
            (
                participant_id,
                conference_id,
                ParticipantConferenceStatus.INVITED.value,
                ParticipantConferenceStatus.APPROVED.value,
                ParticipantConferenceStatus.REGISTERED.value,
            ),
        )
        conference_data = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return ConferenceModel(*conference_data) if conference_data else None

def get_conference_for_organizer(conference_id, organizer_id):
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type