-- ================================================================
-- Migration: Add temporal_analysis column to documents table
-- ================================================================
-- Purpose: Store temporal metadata extracted by the temporal_analyzer
--          LLM node for all documents (notices, announcements, etc.)
--
-- Schema: public.documents
-- Column: temporal_analysis JSONB NULL
--
-- This column will store JSON with structure:
-- {
--   "notice_date": "YYYY-MM-DD",
--   "notice_day": "Monday | Tuesday | ...",
--   "temporal_type": "DATE_SPECIFIC | PERIOD | ONGOING | ...",
--   "valid_from": "YYYY-MM-DD" | null,
--   "valid_until": "YYYY-MM-DD" | null,
--   "events": [
--     {
--       "event": "পরীক্ষা",
--       "condition": null | "...",
--       "event_from": "YYYY-MM-DD" | null,
--       "event_until": "YYYY-MM-DD" | null
--     }
--   ],
--   "expiration_date": "YYYY-MM-DD" | null
-- }
--
-- Usage:
--   psql -h <host> -U <user> -d <database> -f add_temporal_analysis_column.sql
--
-- Or from Python:
--   conn.execute(open('add_temporal_analysis_column.sql').read())
-- ================================================================

BEGIN;

-- Add temporal_analysis column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'documents'
          AND column_name = 'temporal_analysis'
    ) THEN
        ALTER TABLE public.documents
        ADD COLUMN temporal_analysis JSONB NULL;

        RAISE NOTICE 'Column temporal_analysis added to public.documents';
    ELSE
        RAISE NOTICE 'Column temporal_analysis already exists in public.documents';
    END IF;
END $$;

-- Create a GIN index on temporal_analysis for efficient JSON queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'documents'
          AND indexname = 'idx_documents_temporal_analysis'
    ) THEN
        CREATE INDEX idx_documents_temporal_analysis
        ON public.documents USING GIN (temporal_analysis);

        RAISE NOTICE 'Index idx_documents_temporal_analysis created';
    ELSE
        RAISE NOTICE 'Index idx_documents_temporal_analysis already exists';
    END IF;
END $$;

-- Optional: Create functional indexes for common queries

-- Index on notice_date for date-based filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'documents'
          AND indexname = 'idx_documents_temporal_notice_date'
    ) THEN
        CREATE INDEX idx_documents_temporal_notice_date
        ON public.documents ((temporal_analysis->>'notice_date'));

        RAISE NOTICE 'Index idx_documents_temporal_notice_date created';
    ELSE
        RAISE NOTICE 'Index idx_documents_temporal_notice_date already exists';
    END IF;
END $$;

-- Index on temporal_type for filtering by type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'documents'
          AND indexname = 'idx_documents_temporal_type'
    ) THEN
        CREATE INDEX idx_documents_temporal_type
        ON public.documents ((temporal_analysis->>'temporal_type'));

        RAISE NOTICE 'Index idx_documents_temporal_type created';
    ELSE
        RAISE NOTICE 'Index idx_documents_temporal_type already exists';
    END IF;
END $$;

-- Index on expiration_date for expired/active filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'documents'
          AND indexname = 'idx_documents_temporal_expiration'
    ) THEN
        CREATE INDEX idx_documents_temporal_expiration
        ON public.documents ((temporal_analysis->>'expiration_date'));

        RAISE NOTICE 'Index idx_documents_temporal_expiration created';
    ELSE
        RAISE NOTICE 'Index idx_documents_temporal_expiration already exists';
    END IF;
END $$;

COMMIT;

-- ================================================================
-- Example queries after migration:
-- ================================================================

-- 1. Find all documents expiring today or in the future:
-- SELECT doc_id, chunk_id, temporal_analysis->>'expiration_date' AS exp_date
-- FROM public.documents
-- WHERE (temporal_analysis->>'expiration_date') IS NOT NULL
--   AND (temporal_analysis->>'expiration_date')::date >= CURRENT_DATE
-- ORDER BY (temporal_analysis->>'expiration_date')::date;

-- 2. Find all DATE_SPECIFIC documents:
-- SELECT doc_id, chunk_id, temporal_analysis->>'temporal_type' AS type
-- FROM public.documents
-- WHERE temporal_analysis->>'temporal_type' = 'DATE_SPECIFIC';

-- 3. Find documents with events happening on a specific date:
-- SELECT doc_id, chunk_id, event
-- FROM public.documents,
--      jsonb_array_elements(temporal_analysis->'events') AS event
-- WHERE event->>'event_from' = '2026-08-15'
--    OR event->>'event_until' = '2026-08-15';

-- 4. Find all ongoing/permanent information:
-- SELECT doc_id, chunk_id, content
-- FROM public.documents
-- WHERE temporal_analysis->>'temporal_type' = 'ONGOING'
--    OR temporal_analysis->>'temporal_type' = 'TIME_INDEPENDENT';
