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


def fetch_conference_log(conference_id = None, user_id = None, action = None):
    """
    Reads conference audit log data from database.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    sql = f"""SELECT a.conference_id, a.timestamp, a.user_id, a.action, a.invitee
    FROM {CONFERENCE_AUDIT_TABLE} a 
    {"WHERE u.conference_id = %s" if conference_id is not None else ""}
    {"WHERE u.user_id = %s" if user_id is not None else ""}
    {"WHERE u.action = %s" if action is not None else ""}
    ORDER BY a.timestamp DESC
    ;"""

    cursor.execute(sql, [x for x in [conference_id, user_id, action] if x is not None])
    log_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return log_data