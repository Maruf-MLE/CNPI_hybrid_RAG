-- ================================================================
-- Migration: Add temporal_analysis column to notices table
-- ================================================================
-- Purpose: Store temporal metadata for notices
--
-- Schema: public.notices
-- Column: temporal_analysis JSONB NULL
--
-- Usage:
--   psql -h <host> -U <user> -d <database> -f add_notices_temporal_column.sql
-- ================================================================

BEGIN;

-- Add temporal_analysis column to notices table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'notices'
          AND column_name = 'temporal_analysis'
    ) THEN
        ALTER TABLE public.notices
        ADD COLUMN temporal_analysis JSONB NULL;

        RAISE NOTICE 'Column temporal_analysis added to public.notices';
    ELSE
        RAISE NOTICE 'Column temporal_analysis already exists in public.notices';
    END IF;
END $$;

-- Create a GIN index on temporal_analysis for efficient JSON queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'notices'
          AND indexname = 'idx_notices_temporal_analysis'
    ) THEN
        CREATE INDEX idx_notices_temporal_analysis
        ON public.notices USING GIN (temporal_analysis);

        RAISE NOTICE 'Index idx_notices_temporal_analysis created';
    ELSE
        RAISE NOTICE 'Index idx_notices_temporal_analysis already exists';
    END IF;
END $$;

-- Index on notice_date for date-based filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'notices'
          AND indexname = 'idx_notices_temporal_notice_date'
    ) THEN
        CREATE INDEX idx_notices_temporal_notice_date
        ON public.notices ((temporal_analysis->>'notice_date'));

        RAISE NOTICE 'Index idx_notices_temporal_notice_date created';
    ELSE
        RAISE NOTICE 'Index idx_notices_temporal_notice_date already exists';
    END IF;
END $$;

-- Index on temporal_type for filtering by type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'notices'
          AND indexname = 'idx_notices_temporal_type'
    ) THEN
        CREATE INDEX idx_notices_temporal_type
        ON public.notices ((temporal_analysis->>'temporal_type'));

        RAISE NOTICE 'Index idx_notices_temporal_type created';
    ELSE
        RAISE NOTICE 'Index idx_notices_temporal_type already exists';
    END IF;
END $$;

-- Index on expiration_date for expired/active filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'notices'
          AND indexname = 'idx_notices_temporal_expiration'
    ) THEN
        CREATE INDEX idx_notices_temporal_expiration
        ON public.notices ((temporal_analysis->>'expiration_date'));

        RAISE NOTICE 'Index idx_notices_temporal_expiration created';
    ELSE
        RAISE NOTICE 'Index idx_notices_temporal_expiration already exists';
    END IF;
END $$;

COMMIT;

-- ================================================================
-- Example queries after migration:
-- ================================================================

-- 1. Find all notices expiring today or in the future:
-- SELECT notice_id, title_bn, temporal_analysis->>'expiration_date' AS exp_date
-- FROM public.notices
-- WHERE (temporal_analysis->>'expiration_date') IS NOT NULL
--   AND (temporal_analysis->>'expiration_date')::date >= CURRENT_DATE
-- ORDER BY (temporal_analysis->>'expiration_date')::date;

-- 2. Find all DATE_SPECIFIC notices:
-- SELECT notice_id, title_bn, temporal_analysis->>'temporal_type' AS type
-- FROM public.notices
-- WHERE temporal_analysis->>'temporal_type' = 'DATE_SPECIFIC';
