"""Extension and version check — fixed"""
import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST","localhost"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT","5432"),
)
cur = conn.cursor()

cur.execute("SELECT version()")
ver = cur.fetchone()[0]
print("PostgreSQL:", ver[:70])

# pg_available_extensions check
cur.execute("SELECT name FROM pg_available_extensions WHERE name IN ('vector','pg_trgm') ORDER BY name")
avail = [e[0] for e in cur.fetchall()]
print("Available extensions:", avail)

# installed extensions — correct column is extname
cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector','pg_trgm') ORDER BY extname")
installed = [e[0] for e in cur.fetchall()]
print("Installed extensions:", installed)

# vector available?
if 'vector' not in avail:
    print()
    print("[!] pgvector is NOT available on this PostgreSQL installation.")
    print("[!] Install pgvector: https://github.com/pgvector/pgvector")
else:
    print()
    print("[OK] pgvector is available — can be created with: CREATE EXTENSION vector;")

conn.close()
