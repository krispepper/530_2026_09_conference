from datetime import datetime

from db import CONFERENCE_TABLE, get_connection

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
        (organizer_id, name, description, event_datetime, location,
         registration_type, is_published, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, FALSE, NULL)"""
    try:
        cursor.execute(sql, (
            organizer_id, name, description, event_datetime, location,
            registration_type,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_conference_by_id(conference_id):
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, is_published,
        created_at, published_at
        FROM `{CONFERENCE_TABLE}`
        WHERE conference_id = %s AND is_published = TRUE"""
    try:
        cursor.execute(sql, (conference_id,))
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
        WHERE is_published = TRUE
        ORDER BY event_datetime"""
    try:
        cursor.execute(sql)
        conference_data = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return [ConferenceModel(*data) for data in conference_data]


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
