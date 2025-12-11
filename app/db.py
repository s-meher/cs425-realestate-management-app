import psycopg2
import psycopg2.extras


def get_connection():
    """
    Open a new database connection with the search_path set to the realestate schema.
    Adjust credentials as needed for your local setup.
    """
    return psycopg2.connect(
        dbname="realestate_db",
        user="postgres",
        password="1234",
        host="localhost",
        port=5432,
        options="-c search_path=realestate,public",
    )


def dict_cursor(conn):
    """Return a cursor that returns dictionary-like rows."""
    conn = get_connection()
    cursor_factory=psycopg2.extras.RealDictCursor
