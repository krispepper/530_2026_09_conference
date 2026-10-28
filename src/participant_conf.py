# AI assistance: ChatGPT helped protect past attendance records.
# Purpose: Manage invitations, registrations, and cancellations.
# AI assistance: ChatGPT helped enforce conference seat capacity.
from enum import Enum
from uuid import uuid4

from db import (
    CONFERENCE_TABLE,
    PARTICIPANT_CONFERENCE_TABLE,
    USER_TABLE,
    get_connection,
)

from audit_log import log_conference_action, log_conference_invite


class ParticipantConferenceStatus(str, Enum):
    """Defines the allowed participant-conference relationship statuses."""

    INVITED = "invited"
    APPROVED = "approved"
    REGISTERED = "registered"


class ParticipantConferenceModel:
    def __init__(
        self,
        participant_id,
        conference_id,
        status,
        invited_at,
        registered_at,
    ):
        self.participant_id = participant_id
        self.conference_id = conference_id
        self.status = ParticipantConferenceStatus(status)
        self.invited_at = invited_at
        self.registered_at = registered_at


def get_participant_conference_status(participant_id, conference_id):
    """
    Gets a participant's current status for a conference.
    @return: status string or None
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT status
                FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s""",
            (participant_id, conference_id),
        )
        status = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return ParticipantConferenceStatus(status[0]).value if status else None


def get_conference_participants(conference_id):
    """
    Gets participant data associated with a conference for CSV export.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT u.user_id, u.f_name, u.l_name, u.email,
                       pc.status, pc.invited_at, pc.registered_at
                FROM `{PARTICIPANT_CONFERENCE_TABLE}` pc
                JOIN `{USER_TABLE}` u ON u.user_id = pc.participant_id
                WHERE pc.conference_id = %s
                ORDER BY u.l_name, u.f_name, u.user_id""",
            (conference_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


#TODO: try to simplify the function...
def invite_participant(participant_id, conference_id, organizer_id, is_admin=False):
    """
    Creates an invitation for a participant to a restricted conference.
    @return: ParticipantConferenceModel
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT c.conference_id
                FROM `{CONFERENCE_TABLE}` c
                WHERE c.conference_id = %s
                  AND (c.organizer_id = %s OR %s = TRUE)
                  AND c.registration_type = 'restricted'""",
            (conference_id, organizer_id, is_admin),
        )
        if cursor.fetchone() is None:
            raise ValueError("Conference was not found or is not restricted.")

        cursor.execute(
            f"""SELECT user_id FROM `{USER_TABLE}`
                WHERE user_id = %s AND is_participant = TRUE""",
            (participant_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError("Participant was not found.")

        cursor.execute(
            f"""SELECT participant_id, conference_id, status, invited_at,
                       registered_at
                FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        existing = cursor.fetchone()
        if existing:
            connection.commit()
            return ParticipantConferenceModel(*existing)

        cursor.execute(
            f"""INSERT INTO `{PARTICIPANT_CONFERENCE_TABLE}`
                (participant_id, conference_id, status)
            VALUES (%s, %s, %s)""",
            (
                participant_id,
                conference_id,
                ParticipantConferenceStatus.INVITED.value,
            ),
        )
        log_conference_invite(conference_id, organizer_id, participant_id)
        connection.commit()
        return ParticipantConferenceModel(
            participant_id,
            conference_id,
            ParticipantConferenceStatus.INVITED,
            None,
            None,
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def register_participant(participant_id, conference_id, is_admin=False):
    """
    Registers a participant for a published conference.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT registration_type, is_published, capacity, registration_deadline FROM
                FROM `{CONFERENCE_TABLE}`
                WHERE conference_id = %s FOR UPDATE""",
            (conference_id,),
        )
        conference = cursor.fetchone()
        if conference is None or not conference[1]:
            raise ValueError("Conference was not found or is not published.")

        cursor.execute(
            f"""SELECT u.user_id
                FROM `{USER_TABLE}` u
                LEFT JOIN `{CONFERENCE_TABLE}` owned
                    ON owned.organizer_id = u.user_id
                   AND owned.conference_id = %s
                WHERE u.user_id = %s
                  AND (u.is_participant = TRUE OR u.is_admin = TRUE)
                  AND NOT (u.is_organizer = TRUE
                           AND owned.conference_id IS NOT NULL)""",
            (conference_id, participant_id),
        )
        if cursor.fetchone() is None:
            raise PermissionError("You are not permitted to register for this conference.")

        registration_type, _, capacity, registration_deadline = conference
from datetime import datetime
if registration_deadline and datetime.now() > registration_deadline:
    raise ValueError("Registration deadline has passed - registration is closed")

        # Lock the conference first to serialize competing registrations.
        cursor.execute(
            f"""SELECT status FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        existing = cursor.fetchone()
        if existing and existing[0] == ParticipantConferenceStatus.REGISTERED.value:
            connection.commit()
            return

        if capacity is None:
            raise ValueError("Seat capacity has not been set.")

        # Count only active registrations using a current, locking read.
        cursor.execute(
            f"""SELECT participant_id FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE conference_id = %s AND status = %s
                FOR UPDATE""",
            (conference_id, ParticipantConferenceStatus.REGISTERED.value),
        )
        registered_count = len(cursor.fetchall())
        if registered_count >= capacity:
            raise ValueError("This conference is full.")

        if registration_type == "restricted" and not is_admin:
            registration_number = str(uuid4())
            cursor.execute(
                f"""UPDATE `{PARTICIPANT_CONFERENCE_TABLE}`
                    SET status = %s, registered_at = CURRENT_TIMESTAMP,
                        registration_number = %s
                    WHERE participant_id = %s AND conference_id = %s
                      AND status IN (%s, %s)""",
                (
                    ParticipantConferenceStatus.REGISTERED.value,
                    registration_number,
                    participant_id,
                    conference_id,
                    ParticipantConferenceStatus.INVITED.value,
                    ParticipantConferenceStatus.APPROVED.value,
                ),
            )
            if cursor.rowcount != 1:
                raise PermissionError(
                    "An invitation or approval is required to register."
                )
        else:
            registration_number = str(uuid4())
            cursor.execute(
                f"""INSERT INTO `{PARTICIPANT_CONFERENCE_TABLE}`
                    (participant_id, conference_id, status, registered_at,
                     registration_number)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
                    ON DUPLICATE KEY UPDATE
                        registration_number = IF(status = %s,
                                                 registration_number, %s),
                        registered_at = IF(status = %s,
                                           registered_at, CURRENT_TIMESTAMP),
                        status = IF(status = %s, status, %s)""",
                (
                    participant_id,
                    conference_id,
                    ParticipantConferenceStatus.REGISTERED.value,
                    registration_number,
                    ParticipantConferenceStatus.REGISTERED.value,
                    registration_number,
                    ParticipantConferenceStatus.REGISTERED.value,
                    ParticipantConferenceStatus.REGISTERED.value,
                    ParticipantConferenceStatus.REGISTERED.value,
                ),
            )
        connection.commit()
        log_conference_action(conference_id, participant_id, "REGISTER")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def unregister_participant(participant_id, conference_id):
    """
    Unregisters a participant from a conference.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        # Preserve attendance history once the conference has started.
        cursor.execute(
            f"""SELECT event_datetime > CURRENT_TIMESTAMP
                FROM `{CONFERENCE_TABLE}`
                WHERE conference_id = %s FOR UPDATE""",
            (conference_id,),
        )
        conference = cursor.fetchone()
        if conference is None:
            raise ValueError("Conference was not found.")
        if not conference[0]:
            raise ValueError(
                "Cannot cancel after the conference has started."
            )

        cursor.execute(
            f"""DELETE FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s
                  AND conference_id = %s
                  AND status = %s""",
            (
                participant_id,
                conference_id,
                ParticipantConferenceStatus.REGISTERED.value,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("You are not registered for this conference.")
        connection.commit()
        log_conference_action(conference_id, participant_id, "UNREGISTER")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
def remove_participant(participant_id, conference_id, organizer_id):
    """
    Organizer removes a participant from a conference.
    @return: True if removed
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        # 1. Verify organizer owns this conference
        cursor.execute(
            f"""SELECT organizer_id FROM `{CONFERENCE_TABLE}`
                WHERE conference_id = %s FOR UPDATE""",
            (conference_id,),
        )
        conf = cursor.fetchone()
        if conf is None or conf[0] != organizer_id:
            raise PermissionError("Only the organizer can remove participants.")

        # 2. Verify participant is in the conference
        cursor.execute(
            f"""SELECT participant_id FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        if cursor.fetchone() is None:
            raise ValueError("Participant is not in this conference.")

        # 3. Remove
        cursor.execute(
            f"""DELETE FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s""",
            (participant_id, conference_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Could not remove participant.")

        connection.commit()
        log_conference_action(conference_id, organizer_id, f"REMOVE participant {participant_id}")
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

def change_participant_role(participant_id, conference_id, organizer_id, new_status):
    """
    Organizer changes a participant's status/role.
    new_status must be one of: invited, approved, registered
    """
    if new_status not in [s.value for s in ParticipantConferenceStatus]:
        raise ValueError("Invalid status. Use invited, approved, or registered.")

    connection = get_connection()
    cursor = connection.cursor()
    try:
        # 1. Verify organizer owns this conference
        cursor.execute(
            f"""SELECT organizer_id FROM `{CONFERENCE_TABLE}`
                WHERE conference_id = %s FOR UPDATE""",
            (conference_id,),
        )
        conf = cursor.fetchone()
        if conf is None or conf[0] != organizer_id:
            raise PermissionError("Only the organizer can change participant role.")

        # 2. Verify participant exists in conference
        cursor.execute(
            f"""SELECT participant_id FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        if cursor.fetchone() is None:
            raise ValueError("Participant is not in this conference.")

        # 3. Update role/status
        cursor.execute(
            f"""UPDATE `{PARTICIPANT_CONFERENCE_TABLE}`
                SET status = %s
                WHERE participant_id = %s AND conference_id = %s""",
            (new_status, participant_id, conference_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Could not update participant role.")

        connection.commit()
        log_conference_action(conference_id, organizer_id, f"CHANGE ROLE participant {participant_id} to {new_status}")
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()



def get_participant_upcoming_attendance(participant_id):
    """
    Provides information about conferences that a given participant is registered for.
    """
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    sql = f"""SELECT pc.status, pc.registered_at,
        c.name, c.description, c.event_datetime, c.location
        FROM (SELECT * FROM `{PARTICIPANT_CONFERENCE_TABLE}` WHERE participant_id LIKE %s ESCAPE '') pc
        JOIN (SELECT * FROM `{CONFERENCE_TABLE}` WHERE event_datetime > NOW()) c ON c.conference_id = pc.conference_id
        ORDER BY c.event_datetime ASC
        ;"""

    cursor.execute(sql, (participant_id,))
    data = cursor.fetchall()

    cursor.close()
    connection.close()

    return data


def get_all_upcoming_attendance():
    """Provides all upcoming registrations for administrators."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            f"""SELECT pc.participant_id, pc.status, pc.registered_at,
                       u.f_name, u.l_name, u.email,
                       c.name, c.description, c.event_datetime, c.location
                FROM `{PARTICIPANT_CONFERENCE_TABLE}` pc
                JOIN `{USER_TABLE}` u ON u.user_id = pc.participant_id
                JOIN `{CONFERENCE_TABLE}` c
                    ON c.conference_id = pc.conference_id
                WHERE c.event_datetime > NOW()
                ORDER BY c.event_datetime ASC, u.l_name, u.f_name"""
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_registration_receipt(participant_id, conference_id):
    """Return receipt data only for the participant's own registration."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT u.f_name, u.l_name, pc.registration_number,
                       pc.registered_at, c.name, c.event_datetime,
                       c.location, c.description
                FROM `{PARTICIPANT_CONFERENCE_TABLE}` pc
                JOIN `{USER_TABLE}` u ON u.user_id = pc.participant_id
                JOIN `{CONFERENCE_TABLE}` c ON c.conference_id = pc.conference_id
                WHERE pc.participant_id = %s
                  AND pc.conference_id = %s
                  AND pc.status = %s""",
            (
                participant_id,
                conference_id,
                ParticipantConferenceStatus.REGISTERED.value,
            ),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
