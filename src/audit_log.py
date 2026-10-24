from db import get_connection, CONFERENCE_AUDIT_TABLE



def log_conference_action(conference_id, user_id, action):
    """
    Creates an entry in the conference audit log.
    """

    connection = get_connection()
    cursor = connection.cursor()

    sql = f"""INSERT INTO {CONFERENCE_AUDIT_TABLE} (conference_id, user_id, action)
    VALUES (%s, %s, %s)"""

    cursor.execute(sql, (conference_id, user_id, action))
    print(f"Logged conference {action} action {cursor.lastrowid}")

    connection.commit()

    cursor.close()
    connection.close()

def log_conference_invite(conference_id, user_id, invitee):
    """
    Creates an entry in the conference audit log.
    """

    connection = get_connection()
    cursor = connection.cursor()

    sql = f"""INSERT INTO {CONFERENCE_AUDIT_TABLE} (conference_id, user_id, invitee, action)
    VALUES (%s, %s, %s, %s)"""

    cursor.execute(sql, (conference_id, user_id, invitee, "INVITE"))
    print(f"Logged conference INVITE action {cursor.lastrowid}")

    connection.commit()

    cursor.close()
    connection.close()


def fetch_conference_log(
    conference_id=None, user_id=None, action=None, owner_id=None
):
    """
    Reads conference audit log data from database.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    conditions = []
    parameters = []
    if owner_id is not None:
        conditions.append(
            "EXISTS (SELECT 1 FROM conference c "
            "WHERE c.conference_id = a.conference_id AND c.organizer_id = %s)"
        )
        parameters.append(owner_id)
    for column, value in (
        ("a.conference_id", conference_id),
        ("a.user_id", user_id),
        ("a.action", action),
    ):
        if value is not None:
            conditions.append(f"{column} LIKE %s ESCAPE ''")
            parameters.append(value)

    sql = f"""SELECT a.conference_id, a.timestamp, a.user_id, a.action, a.invitee
    FROM {CONFERENCE_AUDIT_TABLE} a
    {"WHERE " + " AND ".join(conditions) if conditions else ""}
    ORDER BY a.timestamp DESC;"""

    cursor.execute(sql, parameters)
    log_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return log_data