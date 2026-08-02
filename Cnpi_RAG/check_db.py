"""
Database check script — documents table exists কিনা দেখবে
এবং সব existing tables list করবে
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", "5432"),
)
cur = conn.cursor()

# ------- 1. সব tables list -------
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
tables = [row[0] for row in cur.fetchall()]

print("=" * 50)
print("  Existing tables in DB")
print("=" * 50)
for t in tables:
    print(f"  - {t}")

# ------- 2. documents table আছে কিনা -------
print()
doc_exists = "documents" in tables
print(f"  documents table exists : {doc_exists}")

if doc_exists:
    # ------- 3. documents table এর columns -------
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'documents'
        ORDER BY ordinal_position
    """)
    cols = cur.fetchall()
    print()
    print("=" * 50)
    print("  documents table columns")
    print("=" * 50)
    for col in cols:
        nullable = "NULL" if col[2] == "YES" else "NOT NULL"
        default  = f"  DEFAULT {col[3]}" if col[3] else ""
        print(f"  {col[0]:<20} {col[1]:<30} {nullable}{default}")

    # ------- 4. documents table এর indexes -------
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'documents'
        ORDER BY indexname
    """)
    indexes = cur.fetchall()
    print()
    print("=" * 50)
    print("  documents table indexes")
    print("=" * 50)
    for idx in indexes:
        print(f"  {idx[0]}")
        print(f"    {idx[1]}")

    # ------- 5. row count -------
    cur.execute("SELECT COUNT(*) FROM public.documents")
    count = cur.fetchone()[0]
    print()
    print(f"  Total rows in documents : {count}")

else:
    print()
    print("  [!] documents table does NOT exist yet.")
    print("  [!] Run: G:\\CNPI_Hybrid_RAG\\Cnpi_RAG\\database\\documents_table.sql")

print()
print("=" * 50)
cur.close()
conn.close()
