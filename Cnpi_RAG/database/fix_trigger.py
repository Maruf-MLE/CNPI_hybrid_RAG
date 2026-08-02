"""
Trigger fix script — set_updated_at function and trigger create করবে।
documents table already created, শুধু trigger বাকি।
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
conn.autocommit = True
cur = conn.cursor()

print("[1/3] Creating set_updated_at() function...")
cur.execute("""
    CREATE OR REPLACE FUNCTION public.set_updated_at()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $func$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $func$;
""")
print("  [OK] function created")

print("[2/3] Dropping old trigger if exists...")
cur.execute("DROP TRIGGER IF EXISTS trg_documents_updated_at ON public.documents;")
print("  [OK] done")

print("[3/3] Creating trigger...")
cur.execute("""
    CREATE TRIGGER trg_documents_updated_at
        BEFORE UPDATE ON public.documents
        FOR EACH ROW
        EXECUTE FUNCTION public.set_updated_at();
""")
print("  [OK] trigger created")

# Verify trigger exists
cur.execute("""
    SELECT trigger_name, event_manipulation, action_timing
    FROM information_schema.triggers
    WHERE event_object_table = 'documents'
    AND trigger_schema = 'public'
""")
triggers = cur.fetchall()
print()
print("=== Triggers on documents table ===")
for t in triggers:
    print(f"  {t[0]} | {t[1]} | {t[2]}")

cur.close()
conn.close()
print()
print("Done! Trigger setup complete.")
