# Purpose: Manage conference waiting lists.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft waiting-list operations.

from db import (
    CONFERENCE_TABLE,
    PARTICIPANT_CONFERENCE_TABLE,
    USER_TABLE,
    WAITING_LIST_TABLE,
    get_connection,
)


def lock_conference(cursor, conference_id):
    """Lock the conference before changing its queue or registrations."""
    cursor.execute(
        f"""SELECT registration_type, capacity, is_published,
                   event_datetime > CURRENT_TIMESTAMP,
                   (registration_deadline IS NULL
                    OR registration_deadline > CURRENT_TIMESTAMP)
            FROM `{CONFERENCE_TABLE}`
            WHERE conference_id = %s FOR UPDATE""",
        (conference_id,),
    )
    conference = cursor.fetchone()
    if conference is None:
        raise ValueError("Conference was not found.")
    return conference


def join_waiting_list(participant_id, conference_id):
    """Join a full conference's queue without changing invitation status."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        registration_type, capacity, published, future, before_deadline = (
            lock_conference(cursor, conference_id)
        )

        cursor.execute(
            f"""SELECT is_participant, is_organizer
                FROM `{USER_TABLE}` WHERE user_id = %s""",
            (participant_id,),
        )
        user = cursor.fetchone()
        if not user or not user[0]:
            raise PermissionError("Participant privileges required.")

        cursor.execute(
            f"""SELECT organizer_id FROM `{CONFERENCE_TABLE}`
                WHERE conference_id = %s""",
            (conference_id,),
        )
        owner = cursor.fetchone()
        if user[1] and owner and owner[0] == participant_id:
            raise PermissionError(
                "You cannot join your own conference's waiting list."
            )

        cursor.execute(
            f"""SELECT status FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        membership = cursor.fetchone()
        status = membership[0] if membership else None

        if status == "registered":
            raise ValueError("You are already registered.")

        cursor.execute(
            f"""SELECT queue_id FROM `{WAITING_LIST_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        if cursor.fetchone() is not None:
            connection.commit()
            return "You are already on the waiting list."

        if not published or not future or not before_deadline:
            raise ValueError("Registration is closed.")
        if capacity is None:
            raise ValueError("Seat capacity has not been set.")
        if registration_type == "restricted" and status not in (
            "invited", "approved"
        ):
            raise PermissionError("An invitation or approval is required.")

        cursor.execute(
            f"""SELECT participant_id
                FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE conference_id = %s AND status = 'registered'
                FOR UPDATE""",
            (conference_id,),
        )
        if len(cursor.fetchall()) < capacity:
            raise ValueError(
                "Seats are available. Register for the conference instead."
            )

        cursor.execute(
            f"""INSERT INTO `{WAITING_LIST_TABLE}`
                (participant_id, conference_id) VALUES (%s, %s)""",
            (participant_id, conference_id),
        )
        connection.commit()
        return "You have joined the waiting list."
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def leave_waiting_list(participant_id, conference_id):
    """Remove only the requesting participant's queue entry."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        lock_conference(cursor, conference_id)
        cursor.execute(
            f"""DELETE FROM `{WAITING_LIST_TABLE}`
                WHERE participant_id = %s AND conference_id = %s""",
            (participant_id, conference_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("You are not on the waiting list.")
        connection.commit()
        return "You have left the waiting list."
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def promote_next_waiting_participant(cursor, conference_id):
    """Fill one free seat in queue order within the caller's transaction."""
    from uuid import uuid4

    registration_type, capacity, published, future, before_deadline = (
        lock_conference(cursor, conference_id)
    )
    if (
        not published or not future or not before_deadline
        or capacity is None or capacity <= 0
    ):
        return None

    cursor.execute(
        f"""SELECT participant_id FROM `{PARTICIPANT_CONFERENCE_TABLE}`
            WHERE conference_id = %s AND status = 'registered'
            FOR UPDATE""",
        (conference_id,),
    )
    if len(cursor.fetchall()) >= capacity:
        return None

    cursor.execute(
        f"""SELECT queue_id, participant_id FROM `{WAITING_LIST_TABLE}`
            WHERE conference_id = %s
            ORDER BY queue_id FOR UPDATE""",
        (conference_id,),
    )
    queue = cursor.fetchall()

    for queue_id, participant_id in queue:
        # Recheck permissions because they may have changed after joining.
        cursor.execute(
            f"""SELECT u.is_participant,
                       (u.is_organizer AND c.organizer_id = u.user_id)
                FROM `{USER_TABLE}` u
                JOIN `{CONFERENCE_TABLE}` c ON c.conference_id = %s
                WHERE u.user_id = %s FOR UPDATE""",
            (conference_id, participant_id),
        )
        user = cursor.fetchone()
        if not user or not user[0] or user[1]:
            continue

        cursor.execute(
            f"""SELECT status FROM `{PARTICIPANT_CONFERENCE_TABLE}`
                WHERE participant_id = %s AND conference_id = %s
                FOR UPDATE""",
            (participant_id, conference_id),
        )
        membership = cursor.fetchone()
        status = membership[0] if membership else None

        if status == "registered":
            # Remove a stale queue entry without consuming another seat.
            cursor.execute(
                f"DELETE FROM `{WAITING_LIST_TABLE}` WHERE queue_id = %s",
                (queue_id,),
            )
            continue

        if registration_type == "restricted" and status not in (
            "invited", "approved"
        ):
            continue

        registration_number = str(uuid4())
        if membership:
            cursor.execute(
                f"""UPDATE `{PARTICIPANT_CONFERENCE_TABLE}`
                    SET status = 'registered',
                        registered_at = CURRENT_TIMESTAMP,
                        registration_number = %s
                    WHERE participant_id = %s AND conference_id = %s""",
                (registration_number, participant_id, conference_id),
            )
        else:
            cursor.execute(
                f"""INSERT INTO `{PARTICIPANT_CONFERENCE_TABLE}`
                    (participant_id, conference_id, status,
                     registered_at, registration_number)
                    VALUES (%s, %s, 'registered', CURRENT_TIMESTAMP, %s)""",
                (participant_id, conference_id, registration_number),
            )

        cursor.execute(
            f"DELETE FROM `{WAITING_LIST_TABLE}` WHERE queue_id = %s",
            (queue_id,),
        )
        return participant_id

    return None


def get_waiting_list_state(participant_id, conference_id):
    """Return queue membership and whether this participant may join."""
    if not participant_id:
        return {"joined": False, "can_join": False}

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT
                EXISTS(
                    SELECT 1 FROM `{WAITING_LIST_TABLE}` w
                    WHERE w.participant_id = u.user_id
                      AND w.conference_id = c.conference_id
                ),
                (
                    u.is_participant = TRUE
                    AND NOT (
                        u.is_organizer = TRUE
                        AND c.organizer_id = u.user_id
                    )
                    AND c.is_published = TRUE
                    AND c.event_datetime > CURRENT_TIMESTAMP
                    AND (
                        c.registration_deadline IS NULL
                        OR c.registration_deadline > CURRENT_TIMESTAMP
                    )
                    AND c.capacity IS NOT NULL
                    AND COALESCE(pc.status, '') <> 'registered'
                    AND (
                        c.registration_type = 'open'
                        OR pc.status IN ('invited', 'approved')
                    )
                    AND (
                        SELECT COUNT(*)
                        FROM `{PARTICIPANT_CONFERENCE_TABLE}` active
                        WHERE active.conference_id = c.conference_id
                          AND active.status = 'registered'
                    ) >= c.capacity
                )
                FROM `{CONFERENCE_TABLE}` c
                JOIN `{USER_TABLE}` u ON u.user_id = %s
                LEFT JOIN `{PARTICIPANT_CONFERENCE_TABLE}` pc
                    ON pc.conference_id = c.conference_id
                    AND pc.participant_id = u.user_id
                WHERE c.conference_id = %s""",
            (participant_id, conference_id),
        )
        row = cursor.fetchone()
        return {
            "joined": bool(row and row[0]),
            "can_join": bool(row and row[1]),
        }
    finally:
        cursor.close()
        connection.close()
