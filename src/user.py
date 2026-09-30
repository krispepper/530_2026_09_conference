from db import get_connection, USER_TABLE



class UserModel:
    def __init__(self, 
            user_id, 
            f_name, l_name, 
            email, 
            is_participant, is_admin, is_organizer):
        self.user_id = user_id
        self.f_name = f_name
        self.l_name = l_name
        self.email = email
        self.is_participant = is_participant
        self.is_admin = is_admin
        self.is_organizer = is_organizer



#TODO: refactor to return user_id just like create_conference() returns conference_id...
def create_user(user_id, f_name, l_name, email, is_participant, is_admin, is_organizer):
    """
    Creates a user in the database.
    """

    connection = get_connection()
    cursor = connection.cursor()

    sql = f"""INSERT INTO {USER_TABLE} (user_id, f_name, l_name, email, is_participant, is_admin, is_organizer)
    VALUES (%s, %s, %s, %s, %s, %s, %s)"""

    cursor.execute(sql, (user_id, f_name, l_name, email, is_participant, is_admin, is_organizer))
    print(f"Added user with id {cursor.lastrowid}")

    connection.commit()

    cursor.close()
    connection.close()

    



def get_user_by_id(user_id):
    """
    Gets a user by their unique user ID.
    @return: UserModel or None
    """

    connection = get_connection()
    cursor = connection.cursor()
    sql = f"""SELECT u.user_id, 
    u.f_name, u.l_name, u.email,
    u.is_participant, u.is_admin, u.is_organizer 
    FROM {USER_TABLE} u 
    WHERE u.user_id = %s;"""


    cursor.execute(sql, [user_id])
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    if user_data is None:
        return user_data
    
    return UserModel(*user_data)

    

def delete_user_by_id(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    sql = f"""
    DELETE FROM {USER_TABLE}
    WHERE user_id = %s;
    """

    cursor.execute(sql, (user_id,))
    connection.commit()

    cursor.close()
    connection.close()
def is_user_organizer(user_id):
    """
    Checks whether a user has organizer privileges.
    @return: True if the user is an organizer, otherwise False
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"SELECT is_organizer FROM `{USER_TABLE}` WHERE user_id = %s"
    try:
        cursor.execute(sql, (user_id,))
        user_data = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return bool(user_data and user_data[0])



#TODO: remove admin privileges, organizer can be the admin...
def is_user_admin(user_id):
    """
    Checks whether a user has administrator privileges.
    @return: True if the user is an administrator, otherwise False
    """
    connection = get_connection()
    cursor = connection.cursor()
    sql = f"SELECT is_admin FROM `{USER_TABLE}` WHERE user_id = %s"
    try:
        cursor.execute(sql, (user_id,))
        user_data = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return bool(user_data and user_data[0])
