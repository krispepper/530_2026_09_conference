
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
        database='edwardhunter'
    )
    
    return connection
    # raise NotImplementedError("Pending group decision on database connection library.")

