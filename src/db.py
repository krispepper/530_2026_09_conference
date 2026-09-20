
import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        user='edwardhunter', 
        password='', 
        host='localhost',
        database='edwardhunter'
    )
    
    return connection
    # raise NotImplementedError("Pending group decision on database connection library.")

