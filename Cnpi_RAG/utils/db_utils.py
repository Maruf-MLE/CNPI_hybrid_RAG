"""
Database Utilities
===================

Wrapper functions for PostgreSQL database operations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
load_dotenv()


def get_db_connection():
    """Get a database connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "college"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            port=os.getenv("DB_PORT", "5432"),
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """
    Execute a SQL query with optional parameters.
    """
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch:
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                return cursor.rowcount

    except Exception as e:
        print(f"Query execution error: {e}")
        if conn:
            conn.rollback()
        return 0 if not fetch else []

    finally:
        if conn:
            conn.close()


def test_connection():
    """Test database connection"""
    conn = get_db_connection()
    if conn:
        print("✓ Database connection successful")
        conn.close()
        return True
    else:
        print("✗ Database connection failed")
        return False


def format_metadata_query(query_text: str) -> str:
    """Prepare a metadata search query for SQL."""
    return f"%{query_text}%"


def optimize_context_for_llm(columns: list, row_dict) -> str:
    """Format query results into a context string for LLM consumption."""
    context_parts = []
    for key, value in row_dict.items():
        value_str = str(value) if value is not None else "NULL"
        context_parts.append(f"{key}: {value_str}")
    return "\n".join(context_parts)


if __name__ == "__main__":
    test_connection()