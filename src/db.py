import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()
print("Loading environment variables...")

USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DB_DEV = os.getenv("DB_NAME_DEV", os.getenv("DB_NAME", "fall2026_530_conf"))
DB_PROD = os.getenv("DB_NAME_PROD", DB_DEV)
IS_PROD = os.getenv("IS_PROD", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DATABASE = DB_PROD if IS_PROD else DB_DEV

USER_TABLE = "user"
CONFERENCE_TABLE = "conference"


def get_connection():
    return mysql.connector.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        database=DATABASE,
    )
print("Using DB:", DATABASE)

def create_user_table_sql():
    return f"""CREATE TABLE IF NOT EXISTS `{USER_TABLE}` (
    `user_id` varchar(10) NOT NULL,
    `f_name` varchar(30) NOT NULL,
    `l_name` varchar(30) NOT NULL,
    `email` varchar(40) NOT NULL,
    `is_admin` BOOL NOT NULL,
    `is_participant` BOOL NOT NULL,
    `is_organizer` BOOL NOT NULL,
    PRIMARY KEY (`user_id`)
    );"""


def create_conference_table_sql():
    return f"""CREATE TABLE IF NOT EXISTS `{CONFERENCE_TABLE}` (
    `conference_id` INT NOT NULL AUTO_INCREMENT,
    `organizer_id` VARCHAR(10) NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `event_datetime` DATETIME NOT NULL,
    `location` VARCHAR(200) NOT NULL,
    `registration_type` ENUM('open', 'restricted') NOT NULL,
    `is_published` BOOL NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `published_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`conference_id`),
    CONSTRAINT `fk_conference_organizer`
        FOREIGN KEY (`organizer_id`) REFERENCES `{USER_TABLE}` (`user_id`),
    INDEX `idx_conference_published_datetime`
        (`is_published`, `event_datetime`)
    );"""


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        for sql in (create_user_table_sql(), create_conference_table_sql()):
            cursor.execute(sql)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
