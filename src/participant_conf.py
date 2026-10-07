from enum import Enum

from db import (
    CONFERENCE_TABLE,
    PARTICIPANT_CONFERENCE_TABLE,
    USER_TABLE,
    get_connection,
)


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
def invite_participant(participant_id, conference_id, organizer_id):
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
                  AND c.organizer_id = %s
                  AND c.registration_type = 'restricted'""",
            (conference_id, organizer_id),
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


def register_participant(participant_id, conference_id):
    """
    Registers a participant for a published conference.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT registration_type, is_published
                FROM `{CONFERENCE_TABLE}`
                WHERE conference_id = %s""",
            (conference_id,),
        )
        conference = cursor.fetchone()
        if conference is None or not conference[1]:
            raise ValueError("Conference was not found or is not published.")

        cursor.execute(
            f"""SELECT user_id FROM `{USER_TABLE}`
                WHERE user_id = %s AND is_participant = TRUE""",
            (participant_id,),
        )
        if cursor.fetchone() is None:
            raise PermissionError("Only participants can register.")

        registration_type, _ = conference
        if registration_type == "restricted":
            cursor.execute(
                f"""UPDATE `{PARTICIPANT_CONFERENCE_TABLE}`
                    SET status = %s, registered_at = CURRENT_TIMESTAMP
                    WHERE participant_id = %s AND conference_id = %s
                      AND status IN (%s, %s)""",
                (
                    ParticipantConferenceStatus.REGISTERED.value,
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
            cursor.execute(
                f"""INSERT INTO `{PARTICIPANT_CONFERENCE_TABLE}`
                    (participant_id, conference_id, status, registered_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        status = IF(status = %s, status, %s),
                        registered_at = IF(status = %s,
                                           registered_at, CURRENT_TIMESTAMP)""",
                (
                    participant_id,
                    conference_id,
                    ParticipantConferenceStatus.REGISTERED.value,
                    ParticipantConferenceStatus.REGISTERED.value,
                    ParticipantConferenceStatus.REGISTERED.value,
                    ParticipantConferenceStatus.REGISTERED.value,
                ),
            )
        connection.commit()
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
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
