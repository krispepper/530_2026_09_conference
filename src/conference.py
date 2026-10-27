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
        registration_deadline,
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
        self.registration_deadline = registration_deadline
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
    capacity,
    registration_deadline,
):
    """
    Creates conference in the database.
    @return: conference_id
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Insert the new conference into the database
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
    """
    Gets a published conference by ID with participant access check.
    Returns conference if user has access via open registration or invite.
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""    SELECT c.conference_id, c.organizer_id, c.name, c.description,
    c.event_datetime, c.location, c.registration_type, c.registration_deadline, c.is_published,
    c.created_at, c.published_at
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
    """
    Gets a conference for organizer view - checks organizer owns it.
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, registration_deadline, is_published,
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

def get_conference_for_admin(conference_id):
    """
    Gets any conference for admin view.
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, registration_deadline, is_published,
        created_at, published_at
        FROM `{CONFERENCE_TABLE}`
        WHERE conference_id = %s"""
    try:
        cursor.execute(sql, (conference_id,))
        conference_data = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return ConferenceModel(*conference_data) if conference_data else None

def publish_conference(conference_id, user_id, is_admin=False):
    """
    Publishes a conference - allows organizer or admin to publish.
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""UPDATE `{CONFERENCE_TABLE}`
        SET is_published = TRUE, published_at = CURRENT_TIMESTAMP
        WHERE conference_id = %s
          AND (organizer_id = %s OR %s = TRUE)
          AND is_published = FALSE"""
    try:
        cursor.execute(sql, (conference_id, user_id, is_admin))
        if cursor.rowcount != 1:
            raise ValueError("Conference was not found or is already published.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

def get_published_conferences(exclude_organizer_id=None):
    """
    Gets all published open conferences, optionally excluding organizer's own.
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, registration_deadline, is_published,
        created_at, published_at
        FROM `{CONFERENCE_TABLE}`
        WHERE is_published = TRUE
          AND registration_type = 'open'
          AND (%s IS NULL OR organizer_id <> %s)
        ORDER BY event_datetime"""
    try:
        cursor.execute(sql, (exclude_organizer_id, exclude_organizer_id))
        conference_data = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return [ConferenceModel(*data) for data in conference_data]

def get_conferences_for_organizer(organizer_id):
    """
    Gets all conferences owned by organizer.
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT conference_id, organizer_id, name, description,
        event_datetime, location, registration_type, registration_deadline, is_published,
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

def get_my_conferences(user_id, is_organizer=False, is_admin=False):
    """
    Gets conferences for current user - admin sees all, organizer sees owned, participant sees registered.
    """
    connection = get_connection()
    cursor = connection.cursor()
    if is_admin:
        sql = f"""SELECT conference_id, organizer_id, name, description,
            event_datetime, location, registration_type, registration_deadline, is_published,
            created_at, published_at
            FROM `{CONFERENCE_TABLE}`
            ORDER BY event_datetime"""
        parameters = ()
    elif is_organizer:
        sql = f"""SELECT conference_id, organizer_id, name, description,
            event_datetime, location, registration_type, registration_deadline, is_published,
            created_at, published_at
            FROM `{CONFERENCE_TABLE}`
            WHERE organizer_id = %s
            ORDER BY event_datetime"""
        parameters = (user_id,)
    else:
        sql = f"""SELECT c.conference_id, c.organizer_id, c.name,
            c.description, c.event_datetime, c.location,
            c.registration_type, c.registration_deadline, c.is_published, c.created_at,
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
    is_owner_view = is_organizer or is_admin
    for data in conference_data:
        conference = ConferenceModel(*data[:11])
        conference.membership_status = (
            "Organizer" if is_owner_view else data[11].capitalize()
        )
        conferences.append(conference)
    return conferences

def validate_conference_form(form):
    """
    Validates conference form data including registration deadline.
    """
    values = {
        "name": form.get("name", "").strip(),
        "description": form.get("description", "").strip(),
        "event_datetime": form.get("event_datetime", "").strip(),
        "location": form.get("location", "").strip(),
        "registration_type": form.get("registration_type", "").strip(),
        "capacity": form.get("capacity", "").strip(),
        "registration_deadline": form.get("registration_deadline", "").strip(),
    }
    errors = {}
    try:
        capacity = int(values["capacity"])
        if capacity <= 0:
            raise ValueError
        values["capacity"] = capacity
    except (ValueError, TypeError):
        errors["capacity"] = "Enter a positive whole number of seats."
    for field in ("name", "description", "event_datetime", "location", "registration_deadline"):
        if not values[field]:
            errors[field] = "This field is required."
    if values["event_datetime"]:
        try:
            values["event_datetime"] = datetime.fromisoformat(values["event_datetime"])
        except ValueError:
            errors["event_datetime"] = "Enter a valid date and time."
    if values["registration_deadline"]:
        try:
            values["registration_deadline"] = datetime.fromisoformat(values["registration_deadline"])
        except ValueError:
            errors["registration_deadline"] = "Enter a valid deadline date and time."
    # deadline must be before event
    if "event_datetime" not in errors and "registration_deadline" not in errors:
        if values["registration_deadline"] and values["event_datetime"]:
            if values["registration_deadline"] >= values["event_datetime"]:
                errors["registration_deadline"] = "Deadline must be before event date."
    if values["registration_type"] not in VALID_REGISTRATION_TYPES:
        errors["registration_type"] = "Choose open or restricted registration."
    return values, errors

def attach_seat_availability(conferences):
    """
    Attaches capacity and remaining seats to conferences by calculating registrations.
    """
    from seats import calculate_remaining_seats
    if not conferences:
        return conferences
    connection = get_connection()
    cursor = connection.cursor()
    placeholders = ", ".join(["%s"] * len(conferences))
    conference_ids = tuple(item.conference_id for item in conferences)
    sql = f"""
        SELECT c.conference_id, c.capacity, COUNT(pc.participant_id)
        FROM `{CONFERENCE_TABLE}` c
        LEFT JOIN `{PARTICIPANT_CONFERENCE_TABLE}` pc
            ON pc.conference_id = c.conference_id
            AND pc.status = 'registered'
        WHERE c.conference_id IN ({placeholders})
        GROUP BY c.conference_id, c.capacity
    """
    try:
        cursor.execute(sql, conference_ids)
        availability = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    finally:
        cursor.close()
        connection.close()
    for conference in conferences:
        capacity, registered_count = availability.get(conference.conference_id, (None, 0))
        conference.capacity = capacity
        conference.remaining_seats = (
            calculate_remaining_seats(capacity, registered_count)
            if capacity is not None else None
        )
    return conferences