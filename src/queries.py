from db import *

def get_test():
    connection = get_connection()
    cursor = connection.cursor(dictionary = True)
    sql = """SELECT message FROM hunter;"""

    cursor.execute(sql)
    test_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return test_data
    # return "<h1>Hello World!</h1>"
