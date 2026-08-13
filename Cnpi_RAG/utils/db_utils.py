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


def get_db_connection(allow_write: bool = False):
    """Get a database connection.

    Prefers a single ``DATABASE_URL`` (e.g. a Neon pooled connection string)
    so SSL and channel-binding params travel with the URL.  Falls back to
    the individual DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / DB_PORT vars
    (with optional DB_SSLMODE) when DATABASE_URL is not set.
    
    Args:
        allow_write: If True, bypass read-only restrictions (for admin panel use only)
    """
    try:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            kwargs = {}
            sslmode = os.getenv("DB_SSLMODE", "").strip()
            if sslmode:
                kwargs["sslmode"] = sslmode
            conn = psycopg2.connect(database_url, **kwargs)
        else:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                database=os.getenv("DB_NAME", "college"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "postgres"),
                port=os.getenv("DB_PORT", "5432"),
                sslmode=os.getenv("DB_SSLMODE", None) or None,
            )
        
        # Mark connection with write permission flag for security checks
        if hasattr(conn, '__dict__'):
            conn.__dict__['_allow_write'] = allow_write
        
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def is_read_only_query(query: str) -> tuple[bool, str]:
    """
    Validate that the query is read-only (SELECT only).
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Empty query not allowed"
    
    # Remove comments and normalize whitespace
    import re
    # Remove single-line comments
    query_clean = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    # Remove multi-line comments
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    # Normalize whitespace
    query_clean = ' '.join(query_clean.split()).strip().upper()
    
    # Check for write operations
    write_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE',
        'EXEC', 'EXECUTE', 'CALL', 'SET', 'DECLARE'
    ]
    
    for keyword in write_keywords:
        # Match keyword as a whole word
        if re.search(rf'\b{keyword}\b', query_clean):
            return False, f"Write operation '{keyword}' not allowed. Only SELECT queries are permitted."
    
    # Must contain SELECT
    if not re.search(r'\bSELECT\b', query_clean):
        return False, "Only SELECT queries are allowed"
    
    # Check for semicolon-separated multiple statements (SQL injection attempt)
    # Allow semicolon only at the end
    query_stripped = query.strip().rstrip(';')
    if ';' in query_stripped:
        return False, "Multiple statements not allowed"
    
    return True, ""


def execute_query(query: str, params: tuple = None, fetch: bool = False, allow_write: bool = False):
    """
    Execute a SQL query with optional parameters.
    
    Security: By default, only SELECT queries are allowed. Any attempt to execute
    INSERT, UPDATE, DELETE, or other write operations will be blocked unless
    allow_write=True is explicitly set (for admin panel use only).
    
    Args:
        query: SQL query to execute
        params: Optional parameters for parameterized query
        fetch: If True, return results; if False, return row count
        allow_write: If True, allow write operations (USE ONLY IN ADMIN PANEL)
    """
    # ★ SECURITY CHECK: Validate read-only query (unless explicitly allowed)
    if not allow_write:
        is_valid, error_msg = is_read_only_query(query)
        if not is_valid:
            print(f"[SECURITY] Query blocked: {error_msg}")
            print(f"[SECURITY] Attempted query: {query[:100]}...")
            raise PermissionError(f"Security violation: {error_msg}")
    
    conn = get_db_connection(allow_write=allow_write)
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