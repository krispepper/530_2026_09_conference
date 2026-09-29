import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()
print("Loading environment variables...")

USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD", "")
HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT")
DB_DEV = os.getenv("DB_NAME_DEV", os.getenv("DB_NAME"))
DB_PROD = os.getenv("DB_NAME_PROD", DB_DEV)
IS_PROD = os.getenv("IS_PROD", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
RESET_ON_STARTUP = os.getenv("DB_RESET_ON_STARTUP", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DATABASE = DB_PROD if IS_PROD else DB_DEV

USER_TABLE = "user"
CONFERENCE_TABLE = "conference"
PARTICIPANT_CONFERENCE_TABLE = "participant_conf"


def get_connection():
    connection_args = {
        "user": USER,
        "password": PASSWORD,
        "host": HOST,
        "database": DATABASE,
    }
    if PORT:
        connection_args["port"] = int(PORT)
    return mysql.connector.connect(**connection_args)


print("Using DB:", DATABASE)


def create_databases():
    connection_args = {
        "user": USER,
        "password": PASSWORD,
        "host": HOST,
    }
    if PORT:
        connection_args["port"] = int(PORT)

    connection = mysql.connector.connect(**connection_args)
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_DEV}`")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_PROD}`")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


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
    `conference_id` VARCHAR(36) NOT NULL,
    `organizer_id` VARCHAR(10) NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `event_datetime` DATETIME NOT NULL,
    `location` VARCHAR(200) NOT NULL,
    `registration_type` ENUM('open', 'restricted') NOT NULL,
    `is_published` BOOL NOT NULL DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `published_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`conference_id`),
    CONSTRAINT `fk_conference_organizer`
        FOREIGN KEY (`organizer_id`) REFERENCES `{USER_TABLE}` (`user_id`),
    INDEX `idx_conference_published_datetime`
        (`is_published`, `event_datetime`)
    );"""


def create_participant_conference_table_sql():
    return f"""CREATE TABLE IF NOT EXISTS `{PARTICIPANT_CONFERENCE_TABLE}` (
    `participant_id` VARCHAR(10) NOT NULL,
    `conference_id` VARCHAR(36) NOT NULL,
    `status` ENUM('invited', 'approved', 'registered') NOT NULL DEFAULT 'invited',
    `invited_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `registered_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`participant_id`, `conference_id`),
    CONSTRAINT `fk_participant_conf_participant`
        FOREIGN KEY (`participant_id`) REFERENCES `{USER_TABLE}` (`user_id`),
    CONSTRAINT `fk_participant_conf_conference`
        FOREIGN KEY (`conference_id`) REFERENCES `{CONFERENCE_TABLE}` (`conference_id`),
    INDEX `idx_participant_conf_conference` (`conference_id`),
    INDEX `idx_participant_conf_status` (`status`)
    );"""


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(create_user_table_sql())
        cursor.execute(create_conference_table_sql())
        cursor.execute(create_participant_conference_table_sql())
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def reset_tables():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"DROP TABLE IF EXISTS `{PARTICIPANT_CONFERENCE_TABLE}`"
        )
        cursor.execute(f"DROP TABLE IF EXISTS `{CONFERENCE_TABLE}`")
        cursor.execute(f"DROP TABLE IF EXISTS `{USER_TABLE}`")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    create_databases()
    print(f"Created or verified databases: {DB_DEV}, {DB_PROD}")
