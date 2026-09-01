-- ============================================================
-- CNPI Hybrid RAG - Performance Optimization Indexes
-- ============================================================
-- Run this on Neon PostgreSQL to improve search performance
-- Expected improvement: 100-150s reduction in query time
-- ============================================================

-- Enable required extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 1. PGVECTOR INDEX (for semantic/vector search)
-- ============================================================
-- IVFFlat index for cosine similarity search
-- lists=100 is optimal for 10k-100k documents
-- Adjust lists based on your document count:
--   - Small dataset (<10k docs): lists=50
--   - Medium dataset (10k-100k docs): lists=100
--   - Large dataset (>100k docs): lists=200

DROP INDEX IF EXISTS idx_documents_embedding_ivfflat;
CREATE INDEX idx_documents_embedding_ivfflat 
ON documents USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Alternative: HNSW index (more accurate but slower to build)
-- Uncomment below if you prefer accuracy over build time
-- DROP INDEX IF EXISTS idx_documents_embedding_hnsw;
-- CREATE INDEX idx_documents_embedding_hnsw 
-- ON documents USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- ============================================================
-- 2. BM25 / FULL-TEXT SEARCH INDEX
-- ============================================================
-- GIN index for tsvector (text search)
DROP INDEX IF EXISTS idx_documents_tsvector_gin;
CREATE INDEX idx_documents_tsvector_gin 
ON documents USING gin(to_tsvector('english', content));

-- Optional: Bengali text search (if using Bengali stemming)
-- CREATE INDEX idx_documents_tsvector_bengali
-- ON documents USING gin(to_tsvector('simple', content));

-- ============================================================
-- 3. METADATA INDEXES (for filtering)
-- ============================================================
-- Date filtering (for temporal queries)
DROP INDEX IF EXISTS idx_documents_meta_date;
CREATE INDEX idx_documents_meta_date 
ON documents ((meta->>'date'));

-- Document type filtering
DROP INDEX IF EXISTS idx_documents_meta_doc_type;
CREATE INDEX idx_documents_meta_doc_type 
ON documents ((meta->>'doc_type'));

-- Priority documents filtering
DROP INDEX IF EXISTS idx_documents_meta_priority;
CREATE INDEX idx_documents_meta_priority 
ON documents ((meta->>'priority'));

-- Priority order (for sorting priority docs)
DROP INDEX IF EXISTS idx_documents_meta_priority_order;
CREATE INDEX idx_documents_meta_priority_order 
ON documents ((meta->>'priority_order'));

-- ============================================================
-- 4. COMPOSITE INDEXES (for combined queries)
-- ============================================================
-- Priority + order (common query pattern)
DROP INDEX IF EXISTS idx_documents_priority_composite;
CREATE INDEX idx_documents_priority_composite 
ON documents ((meta->>'priority'), (meta->>'priority_order'));

-- ============================================================
-- 5. CONTENT LENGTH INDEX (for performance)
-- ============================================================
-- Helps with queries that filter by content length
DROP INDEX IF EXISTS idx_documents_content_length;
CREATE INDEX idx_documents_content_length 
ON documents (length(content));

-- ============================================================
-- 6. VACUUM ANALYZE (refresh statistics)
-- ============================================================
-- This updates query planner statistics for optimal performance
VACUUM ANALYZE documents;

-- ============================================================
-- 7. VERIFY INDEXES
-- ============================================================
-- Check all indexes on documents table
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes
JOIN pg_class ON pg_indexes.indexname = pg_class.relname
WHERE tablename = 'documents'
ORDER BY indexname;

-- ============================================================
-- EXPECTED RESULTS:
-- ============================================================
-- Before: vector_search: 40-80s, bm25_search: 30-60s
-- After:  vector_search: 5-10s,  bm25_search: 3-8s
-- Total reduction: 100-150 seconds
-- ============================================================
