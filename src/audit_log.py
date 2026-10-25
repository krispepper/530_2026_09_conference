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


def fetch_conference_log(conference_id = None, user_id = None, action = None, before = None, after = None):
    """
    Reads conference audit log data from database.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    print("After: " + str(after))

    conditions = [x for x in [
        "a.conference_id LIKE %s ESCAPE ''" if conference_id is not None else None,
        "a.user_id LIKE %s ESCAPE ''" if user_id is not None else None,
        "a.action LIKE %s ESCAPE ''" if action is not None else None,
        "a.timestamp < %s" if before is not None else None,
        "a.timestamp > %s" if after is not None else None,
    ] if x is not None]

    sql = f"""SELECT a.conference_id, a.timestamp, a.user_id, a.action, a.invitee
    FROM {CONFERENCE_AUDIT_TABLE} a 
    {"WHERE " + " AND ".join(conditions) if conditions else ""}
    ORDER BY a.timestamp DESC
    ;"""

    """
    {"WHERE a.conference_id LIKE %s ESCAPE ''" if conference_id is not None else ""}
    {"WHERE a.user_id LIKE %s ESCAPE ''" if user_id is not None else ""}
    {"WHERE a.action LIKE %s ESCAPE ''" if action is not None else ""}
    {"WHERE a.timestamp < %s" if before is not None else ""}
    {"WHERE a.timestamp > %s" if after is not None else ""}
    """

    cursor.execute(sql, [x for x in [conference_id, user_id, action, before, after] if x is not None])
    log_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return log_data