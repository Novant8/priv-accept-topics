import sqlite3
from contextlib import contextmanager
from typing import Generator

DBConnection = sqlite3.Connection

@contextmanager
def db_connection(db_path: str) -> Generator[DBConnection, None, None]:
    """
    Context manager for managing a SQLite database connection.
    """
    conn = sqlite3.connect(db_path, uri=True)
    try:
        yield conn
    finally:
        conn.close()