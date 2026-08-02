"""
documents table create করার script।
pgvector install হওয়ার পরে এটা run করো।

Usage:
    cd G:\CNPI_Hybrid_RAG\Cnpi_RAG
    python database\create_documents_table.py
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

SQL = """
-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Main table
CREATE TABLE IF NOT EXISTS public.documents (

    doc_id      SERIAL          PRIMARY KEY,
    chunk_id    VARCHAR(200)    NOT NULL UNIQUE,
    content     TEXT            NOT NULL
                    CONSTRAINT documents_content_not_empty CHECK (length(trim(content)) > 10),
    doc_type    VARCHAR(100)    NOT NULL DEFAULT 'general',
    topic       VARCHAR(500),
    department  VARCHAR(20)     CHECK (
                    department IS NULL OR
                    department IN ('CST','ET','ENT','RAC','FT','MT','Non-Tech','General')
                ),
    embedding   VECTOR(384)     NOT NULL,
    tsv         TSVECTOR        GENERATED ALWAYS AS (
                    to_tsvector('simple', content)
                ) STORED,
    meta        JSONB           NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    source_file VARCHAR(200)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_embedding
    ON public.documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_tsv
    ON public.documents USING GIN (tsv);

CREATE INDEX IF NOT EXISTS idx_documents_doc_type
    ON public.documents USING btree (doc_type);

CREATE INDEX IF NOT EXISTS idx_documents_department
    ON public.documents USING btree (department);

CREATE INDEX IF NOT EXISTS idx_documents_chunk_id
    ON public.documents USING btree (chunk_id);

CREATE INDEX IF NOT EXISTS idx_documents_meta
    ON public.documents USING GIN (meta);

CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON public.documents USING btree (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_updated_at
    ON public.documents USING btree (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_type_dept
    ON public.documents USING btree (doc_type, department);

-- updated_at auto-update trigger
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_documents_updated_at ON public.documents;

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON public.documents
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();
"""


def create_table():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432"),
    )

    try:
        conn.autocommit = True
        cur = conn.cursor()

        print("[1/4] Checking pgvector availability...")
        cur.execute("SELECT name FROM pg_available_extensions WHERE name = 'vector'")
        if not cur.fetchone():
            print()
            print("ERROR: pgvector extension is NOT available in this PostgreSQL installation.")
            print()
            print("Install pgvector for PostgreSQL 15 on Windows:")
            print("  https://github.com/pgvector/pgvector/releases")
            print()
            print("Download the Windows zip, then copy:")
            print("  vector.dll     -> D:\\ALl installed software\\postgreSQL\\lib\\")
            print("  vector.control -> D:\\ALl installed software\\postgreSQL\\share\\extension\\")
            print("  vector--*.sql  -> D:\\ALl installed software\\postgreSQL\\share\\extension\\")
            print()
            print("After copying, restart PostgreSQL service and run this script again.")
            return False

        print("  [OK] pgvector is available")

        print("[2/4] Creating documents table and extensions...")
        # Execute each statement separately for cleaner error handling
        statements = [s.strip() for s in SQL.split(";") if s.strip()]
        for stmt in statements:
            try:
                cur.execute(stmt)
                print(f"  [OK] {stmt[:60].replace(chr(10),' ')}...")
            except Exception as e:
                print(f"  [SKIP/ERROR] {str(e)[:80]}")

        print()
        print("[3/4] Verifying table creation...")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'documents'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        if cols:
            print(f"  [OK] documents table has {len(cols)} columns:")
            for col in cols:
                print(f"       - {col[0]:<20} {col[1]}")
        else:
            print("  [ERROR] Table was not created.")
            return False

        print()
        print("[4/4] Verifying indexes...")
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'documents'
            ORDER BY indexname
        """)
        indexes = [r[0] for r in cur.fetchall()]
        print(f"  [OK] {len(indexes)} indexes created:")
        for idx in indexes:
            print(f"       - {idx}")

        print()
        print("=" * 50)
        print("  documents table created successfully!")
        print("  Next step: run the seed script to load data.")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    create_table()
