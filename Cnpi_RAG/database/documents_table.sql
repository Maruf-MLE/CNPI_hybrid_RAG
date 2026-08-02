-- =============================================================================
-- CNPI RAG System — documents table
-- SQL Retrieve Path এর জন্য সম্পূর্ণ production-ready schema
--
-- Compatible with:
--   - PostgreSQL 15+
--   - pgvector extension
--   - embedding_utils.py (all-MiniLM-L6-v2 → 384-dim)
--   - bm25_search() uses tsvector_column="tsv", language="simple"
--   - vector_search() uses embedding_column="embedding", metadata_column="meta"
--   - hybrid_search() uses table_name="documents"
--
-- Run order:
--   1. Enable extensions (superuser required)
--   2. Create table
--   3. Create indexes
--   4. Create helper function
-- =============================================================================


-- =============================================================================
-- STEP 1 — Extensions
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector: cosine similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- trigram: fuzzy text matching (already in DB)


-- =============================================================================
-- STEP 2 — Main Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.documents (

    -- -------------------------------------------------------------------------
    -- Primary identity
    -- -------------------------------------------------------------------------

    doc_id      SERIAL          PRIMARY KEY,

    -- JSON file থেকে আসা chunk_id (eg: "academic_rules_chunk_1", "dept_overview_cst")
    -- UNIQUE constraint: একই chunk দুইবার insert হবে না → safe upsert করা যাবে
    chunk_id    VARCHAR(200)    NOT NULL UNIQUE,

    -- -------------------------------------------------------------------------
    -- Core search content — সবসময় English text
    -- এই field-ই embedding এবং BM25 উভয়ের target
    -- -------------------------------------------------------------------------

    content     TEXT            NOT NULL
                    CONSTRAINT documents_content_not_empty CHECK (length(trim(content)) > 10),

    -- -------------------------------------------------------------------------
    -- Classification columns — fast filter + routing এর জন্য
    -- -------------------------------------------------------------------------

    -- doc_type: JSON-এর doc_type field হুবহু (eg: "department_overview",
    --           "teachers info", "academic_rules", "weekly_routine_summary")
    -- NULL হবে না — router এই field দিয়ে category বুঝবে
    doc_type    VARCHAR(100)    NOT NULL DEFAULT 'general',

    -- topic: JSON-এর topic field (eg: "CST 5th Semester — Weekly Class List")
    -- LLM context header হিসেবে ব্যবহার হবে
    topic       VARCHAR(500),

    -- department: department-specific docs এর জন্য (eg: "CST", "FT", "RAC")
    -- institution-wide docs এর জন্য NULL থাকবে
    -- CHECK constraint: সঠিক short_code ছাড়া insert হবে না
    department  VARCHAR(20)     CHECK (
                    department IS NULL OR
                    department IN ('CST','ET','ENT','RAC','FT','MT','Non-Tech','General')
                ),

    -- -------------------------------------------------------------------------
    -- Hybrid search columns
    -- -------------------------------------------------------------------------

    -- pgvector 384-dim embedding (all-MiniLM-L6-v2)
    -- NOT NULL: embedding ছাড়া document retrieve করা সম্ভব না
    embedding   VECTOR(384)     NOT NULL,

    -- GENERATED column: content থেকে auto-computed, manual update লাগবে না
    -- 'simple' dictionary: English + Romanized Bengali উভয়ই handle করে
    -- 'english' dictionary ব্যবহার করলে Bengali words strip হয়ে যায় — তাই 'simple'
    tsv         TSVECTOR        GENERATED ALWAYS AS (
                    to_tsvector('simple', content)
                ) STORED,

    -- -------------------------------------------------------------------------
    -- Flexible metadata — JSON-এর remaining fields সব এখানে
    -- -------------------------------------------------------------------------

    -- meta: structured extras যা LLM context বা filtering এ কাজে লাগতে পারে
    -- eg: {"name": "Md. Subel Ali", "phone": "01737...", "total_teachers": 9}
    -- GIN index থাকবে — JSONB key query fast হবে
    meta        JSONB           NOT NULL DEFAULT '{}',

    -- -------------------------------------------------------------------------
    -- Audit columns — production এ data traceability এর জন্য
    -- -------------------------------------------------------------------------

    -- created_at: কখন insert হয়েছে
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- updated_at: কখন last update হয়েছে (trigger দিয়ে auto-update হবে)
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- source_file: কোন JSON file থেকে এসেছে (debugging এর জন্য)
    -- eg: "department_overview.json", "teachers_data.json"
    source_file VARCHAR(200)

);

-- Table comment
COMMENT ON TABLE public.documents IS
    'CNPI RAG SQL Retrieve Path — সব semantic search documents এক জায়গায়।
     content column embed করে pgvector cosine search + tsvector BM25 hybrid search হয়।
     embedding_utils.hybrid_search() এই table query করে।';

-- Column comments
COMMENT ON COLUMN public.documents.chunk_id IS
    'JSON file এর chunk_id — UNIQUE constraint দিয়ে duplicate insert block করে।
     Safe upsert: INSERT ... ON CONFLICT (chunk_id) DO UPDATE।';

COMMENT ON COLUMN public.documents.content IS
    'Embedding + BM25 উভয়ের target text — সবসময় English।
     Minimum 10 char CHECK constraint আছে — empty content block হবে।';

COMMENT ON COLUMN public.documents.doc_type IS
    'Document category: "department_overview","teachers info","academic_rules",
     "weekly_routine_summary","institution_details" etc.
     Router এই field দিয়ে context categorize করে LLM-কে দেয়।';

COMMENT ON COLUMN public.documents.department IS
    'Department-specific docs এর জন্য short code।
     Institution-wide docs (notices, policies) এ NULL।
     Valid values: CST, ET, ENT, RAC, FT, MT, Non-Tech, General।';

COMMENT ON COLUMN public.documents.embedding IS
    'all-MiniLM-L6-v2 দিয়ে encode করা 384-dim vector।
     IVFFlat index দিয়ে approximate nearest neighbor search হয়।';

COMMENT ON COLUMN public.documents.tsv IS
    'GENERATED column — content থেকে auto-computed tsvector।
     simple dictionary: English + Romanized Bengali handle করে।
     GIN index দিয়ে BM25 full-text search হয়।';

COMMENT ON COLUMN public.documents.meta IS
    'JSON-এর remaining fields — name, phone, total_teachers, room_number etc।
     LLM context এ extra detail দেওয়ার জন্য এবং post-retrieval filtering এর জন্য।';

COMMENT ON COLUMN public.documents.source_file IS
    'কোন JSON file থেকে insert হয়েছে — debugging ও re-seeding এর জন্য।';


-- =============================================================================
-- STEP 3 — Indexes
-- =============================================================================

-- ---------------------------------------------------------------------------
-- A. Vector similarity search (pgvector IVFFlat)
--    lists=100: ~300-500 total documents এর জন্য optimal
--    বেশি documents হলে lists বাড়াতে হবে (sqrt(N) rule of thumb)
--    IMPORTANT: table-এ data থাকার পরে এই index তৈরি করতে হবে
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_embedding
    ON public.documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- B. BM25 full-text search (GIN on tsvector)
--    embedding_utils.bm25_search() এই index ব্যবহার করে
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_tsv
    ON public.documents
    USING GIN (tsv);

-- ---------------------------------------------------------------------------
-- C. doc_type filter — router যখন specific category search করবে
--    eg: WHERE doc_type = 'weekly_routine_summary' AND department = 'CST'
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_doc_type
    ON public.documents
    USING btree (doc_type);

-- ---------------------------------------------------------------------------
-- D. department filter — department-specific queries fast হবে
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_department
    ON public.documents
    USING btree (department);

-- ---------------------------------------------------------------------------
-- E. chunk_id lookup — upsert এবং existence check এর জন্য
--    UNIQUE constraint already creates an index, but explicit for clarity
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_chunk_id
    ON public.documents
    USING btree (chunk_id);

-- ---------------------------------------------------------------------------
-- F. JSONB meta — key-value query fast করার জন্য
--    eg: WHERE meta->>'doc_type' = 'teachers info'
--    eg: WHERE meta @> '{"department": "CST"}'
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_meta
    ON public.documents
    USING GIN (meta);

-- ---------------------------------------------------------------------------
-- G. created_at + updated_at — time-based queries এবং ordering এর জন্য
--    eg: সর্বশেষ update হওয়া documents খুঁজতে
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON public.documents
    USING btree (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_updated_at
    ON public.documents
    USING btree (updated_at DESC);

-- ---------------------------------------------------------------------------
-- H. Composite index — সবচেয়ে common query pattern এর জন্য
--    eg: doc_type + department একসাথে filter
--    embedding_utils তে future filtering support এর জন্য
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_documents_type_dept
    ON public.documents
    USING btree (doc_type, department);


-- =============================================================================
-- STEP 4 — Auto-update trigger for updated_at
-- updated_at manually update করার ঝামেলা এড়ানোর জন্য
-- =============================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
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


-- =============================================================================
-- STEP 5 — Safe Upsert Helper (Python seed script এর জন্য reference)
-- =============================================================================

-- chunk_id conflict হলে content + meta update করবে
-- embedding পুরনো থাকবে যদি content না বদলায়
-- এই pattern টি seed script এ ব্যবহার করতে হবে:
--
-- INSERT INTO public.documents
--     (chunk_id, content, doc_type, topic, department, embedding, meta, source_file)
-- VALUES
--     (%s, %s, %s, %s, %s, %s::vector, %s::jsonb, %s)
-- ON CONFLICT (chunk_id) DO UPDATE SET
--     content     = EXCLUDED.content,
--     doc_type    = EXCLUDED.doc_type,
--     topic       = EXCLUDED.topic,
--     department  = EXCLUDED.department,
--     embedding   = EXCLUDED.embedding,
--     meta        = EXCLUDED.meta,
--     source_file = EXCLUDED.source_file,
--     updated_at  = NOW();


-- =============================================================================
-- STEP 6 — Verification queries (run after seeding)
-- =============================================================================

-- Row count by doc_type:
-- SELECT doc_type, COUNT(*) FROM public.documents GROUP BY doc_type ORDER BY COUNT(*) DESC;

-- Row count by department:
-- SELECT department, COUNT(*) FROM public.documents GROUP BY department ORDER BY COUNT(*) DESC;

-- Check for NULL embeddings (should be 0):
-- SELECT COUNT(*) FROM public.documents WHERE embedding IS NULL;

-- Check for duplicate chunk_ids (should be 0):
-- SELECT chunk_id, COUNT(*) FROM public.documents GROUP BY chunk_id HAVING COUNT(*) > 1;

-- Sample vector search test (replace vector values):
-- SELECT chunk_id, doc_type, LEFT(content, 80) FROM public.documents
-- ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector LIMIT 5;
