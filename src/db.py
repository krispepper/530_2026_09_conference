
import mysql.connector
# importing os module for environment variables
import os
# importing necessary functions from dotenv library
from dotenv import load_dotenv, dotenv_values 
# loading variables from .env file
load_dotenv() 
# export USER="[MySQL username]"
# accessing and printing value
USER = os.getenv("USER")
print('The user is ',USER)


USER_TABLE = "user"

def get_connection():
    connection = mysql.connector.connect(
        user=USER, 
        password='', 
        host='localhost',
        database='fall2026_530_conf'
    )
    
    return connection
    # raise NotImplementedError("Pending group decision on database connection library.")

def create_user_table_sql():
    return f"""CREATE TABLE IF NOT EXISTS `{USER_TABLE}` ( 
    `user_id` varchar(10) NOT NULL, 
    `f_name` varchar(30) NOT NULL, 
    `l_name` varchar(30) NOT NULL, 
    `email` varchar(40) NOT NULL, 
    `is_admin` BOOL NOT NULL, 
    `is_participant` BOOL NOT NULL, 
    `is_organizer` BOOL NOT NULL, 
    PRIMARY KEY (`user_id`) );"""


def create_tables():
    TABLES = {}
    TABLES[USER_TABLE] = create_user_table_sql()

    connection = get_connection()
    cursor = connection.cursor()
    
    for table in TABLES:
        sql = TABLES[table]
        cursor.execute(sql)

    cursor.close()
    connection.close()

create_tables()
