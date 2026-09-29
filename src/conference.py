from datetime import datetime
from uuid import uuid4

from db import CONFERENCE_TABLE, PARTICIPANT_CONFERENCE_TABLE, get_connection
from participant_conf import ParticipantConferenceStatus

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


def create_conference(
    organizer_id,
    name,
    description,
    event_datetime,
    location,
    registration_type,
):
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""INSERT INTO `{CONFERENCE_TABLE}`
        (conference_id, organizer_id, name, description, event_datetime, location,
         registration_type, is_published, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, NULL)"""
    try:
        conference_id = str(uuid4())
        cursor.execute(sql, (
            conference_id, organizer_id, name, description, event_datetime,
            location, registration_type,
        ))
        connection.commit()
        return conference_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_conference_by_id(conference_id, participant_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""    SELECT c.conference_id, c.organizer_id, c.name, c.description,
    c.event_datetime, c.location, c.registration_type, c.is_published,
    c.created_at, c.published_at
        FROM `{CONFERENCE_TABLE}` c
        LEFT JOIN `{PARTICIPANT_CONFERENCE_TABLE}` pc
            ON pc.conference_id = c.conference_id
            AND pc.participant_id = %s
        WHERE c.conference_id = %s
        AND c.is_published = TRUE
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
        event_datetime, location, registration_type, is_published,
        created_at, published_at
        FROM `{CONFERENCE_TABLE}`
        WHERE conference_id = %s AND organizer_id = %s"""
    try:
        cursor.execute(sql, (conference_id, organizer_id))
        conference_data = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return ConferenceModel(*conference_data) if conference_data else None


def publish_conference(conference_id, organizer_id):
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""UPDATE `{CONFERENCE_TABLE}`
        SET is_published = TRUE, published_at = CURRENT_TIMESTAMP
        WHERE conference_id = %s AND organizer_id = %s AND is_published = FALSE"""
    try:
        cursor.execute(sql, (conference_id, organizer_id))
        if cursor.rowcount != 1:
            raise ValueError("Conference was not found or is already published.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_published_conferences():
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, is_published,
        created_at, published_at
        FROM `{CONFERENCE_TABLE}`
        WHERE is_published = TRUE AND registration_type = 'open'
        ORDER BY event_datetime"""
    try:
        cursor.execute(sql)
        conference_data = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return [ConferenceModel(*data) for data in conference_data]


def get_conferences_for_organizer(organizer_id):
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, is_published,
        created_at, published_at
        FROM `{CONFERENCE_TABLE}`
        WHERE organizer_id = %s
        ORDER BY event_datetime"""
    try:
        cursor.execute(sql, (organizer_id,))
        conference_data = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return [ConferenceModel(*data) for data in conference_data]


def get_my_conferences(user_id, is_organizer=False):
    connection = get_connection()
    cursor = connection.cursor()
    if is_organizer:
        sql = f"""SELECT conference_id, organizer_id, name, description,
            event_datetime, location, registration_type, is_published,
            created_at, published_at
            FROM `{CONFERENCE_TABLE}`
            WHERE organizer_id = %s
            ORDER BY event_datetime"""
        parameters = (user_id,)
    else:
        sql = f"""SELECT c.conference_id, c.organizer_id, c.name,
            c.description, c.event_datetime, c.location,
            c.registration_type, c.is_published, c.created_at,
            c.published_at, pc.status
            FROM `{CONFERENCE_TABLE}` c
            JOIN `{PARTICIPANT_CONFERENCE_TABLE}` pc
                ON pc.conference_id = c.conference_id
            WHERE pc.participant_id = %s
            ORDER BY c.event_datetime"""
        parameters = (user_id,)
    try:
        cursor.execute(sql, parameters)
        conference_data = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    conferences = []
    for data in conference_data:
        conference = ConferenceModel(*data[:10])
        conference.membership_status = "Organizer" if is_organizer else data[10].capitalize()
        conferences.append(conference)
    return conferences


def validate_conference_form(form):
    values = {
        "name": form.get("name", "").strip(),
        "description": form.get("description", "").strip(),
        "event_datetime": form.get("event_datetime", "").strip(),
        "location": form.get("location", "").strip(),
        "registration_type": form.get("registration_type", "").strip(),
    }
    errors = {}
    for field in ("name", "description", "event_datetime", "location"):
        if not values[field]:
            errors[field] = "This field is required."
    if values["event_datetime"]:
        try:
            values["event_datetime"] = datetime.fromisoformat(
                values["event_datetime"]
            )
        except ValueError:
            errors["event_datetime"] = "Enter a valid date and time."
    if values["registration_type"] not in VALID_REGISTRATION_TYPES:
        errors["registration_type"] = "Choose open or restricted registration."
    return values, errors
