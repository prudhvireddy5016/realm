import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import settings


def get_connection():
    """Create a new database connection."""
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def query(sql: str, params: tuple = None, fetch_one: bool = False):
    """Execute a query and return results as list of dicts."""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        if cur.description:
            rows = cur.fetchall()
            cur.close()
            return dict(rows[0]) if fetch_one and rows else [dict(r) for r in rows]
        cur.close()
        return None


def execute(sql: str, params: tuple = None):
    """Execute a statement without returning results."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cur.close()


def query_returning(sql: str, params: tuple = None, fetch_one: bool = True):
    """Execute an INSERT/UPDATE with RETURNING clause."""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        if cur.description:
            rows = cur.fetchall()
            cur.close()
            return dict(rows[0]) if fetch_one and rows else [dict(r) for r in rows]
        cur.close()
        return None
