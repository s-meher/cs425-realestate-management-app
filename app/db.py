import psycopg
from psycopg.rows import dict_row


def get_connection():
    """
    Open a new database connection with the search_path set to the realestate schema.
    Adjust credentials as needed for your local setup.
    """
    return psycopg.connect(
        dbname="realestate_db",
        user="shreemeher",
        password="",
        host="localhost",
        port=5432,
        options="-c search_path=realestate,public",
    )


def dict_cursor(conn):
    """Return a cursor that returns dictionary-like rows."""
    return conn.cursor(row_factory=dict_row)
