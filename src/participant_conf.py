from db import (
    CONFERENCE_TABLE,
    PARTICIPANT_CONFERENCE_TABLE,
    USER_TABLE,
    get_connection,
)


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
        self.status = status
        self.invited_at = invited_at
        self.registered_at = registered_at


def invite_participant(participant_id, conference_id, organizer_id):
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
                VALUES (%s, %s, 'invited')""",
            (participant_id, conference_id),
        )
        connection.commit()
        return ParticipantConferenceModel(
            participant_id, conference_id, "invited", None, None
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def register_participant(participant_id, conference_id):
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
                    SET status = 'registered', registered_at = CURRENT_TIMESTAMP
                    WHERE participant_id = %s AND conference_id = %s
                      AND status IN ('invited', 'approved')""",
                (participant_id, conference_id),
            )
            if cursor.rowcount != 1:
                raise PermissionError(
                    "An invitation or approval is required to register."
                )
        else:
            cursor.execute(
                f"""INSERT INTO `{PARTICIPANT_CONFERENCE_TABLE}`
                    (participant_id, conference_id, status, registered_at)
                    VALUES (%s, %s, 'registered', CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        status = IF(status = 'registered', status, 'registered'),
                        registered_at = IF(status = 'registered',
                                           registered_at, CURRENT_TIMESTAMP)""",
                (participant_id, conference_id),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
