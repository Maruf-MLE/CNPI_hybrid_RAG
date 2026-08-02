"""
Embedding & BM25 Search Utilities
===================================

Provides:
  - get_embedding_model()  : SentenceTransformer singleton
  - embed_text(text)       : returns list[float]
  - vector_search(...)     : cosine-similarity search via PostgreSQL pgvector
  - bm25_search(...)       : full-text search via PostgreSQL tsvector/tsquery
  - hybrid_search(...)     : combines vector + BM25 results (RRF fusion)

Environment variables used (from .env):
  EMBEDDING_MODEL     = sentence-transformers/all-MiniLM-L6-v2
  EMBEDDING_DIMENSION = 384
  TOP_K_SEARCH        = 5
"""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
_TOP_K: int = int(os.getenv("TOP_K_SEARCH", "5"))


# =============================================================================
# Embedding model singleton
# =============================================================================

def get_embedding_model():
    """Return a lazily-created SentenceTransformer singleton.

    Keeping a single instance avoids reloading the model weights on every
    graph invocation.  The model is downloaded on first call and cached in
    the HuggingFace local cache directory.
    """
    if not hasattr(get_embedding_model, "_instance"):
        try:
            from sentence_transformers import SentenceTransformer
            get_embedding_model._instance = SentenceTransformer(_EMBEDDING_MODEL_NAME)
            print(f"✓ Embedding model loaded: {_EMBEDDING_MODEL_NAME}")
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from exc
    return get_embedding_model._instance


def embed_text(text: str) -> list[float]:
    """Convert a text string into a dense embedding vector.

    Parameters
    ----------
    text : str
        The text to embed.

    Returns
    -------
    list[float]
        A flat list of floats representing the embedding.
    """
    model = get_embedding_model()
    vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vector.tolist()


# =============================================================================
# PostgreSQL pgvector search
# =============================================================================

def vector_search(
    query_text: str,
    table_name: str = "documents",
    embedding_column: str = "embedding",
    content_column: str = "content",
    metadata_column: str = "meta",
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Semantic similarity search using pgvector cosine distance.

    Expects a table with an `embedding` column of type `vector(N)`.

    Parameters
    ----------
    query_text : str
        The natural-language search query.
    table_name : str
        PostgreSQL table that holds the documents.
    embedding_column : str
        Column name that stores the pgvector embedding.
    content_column : str
        Column name that stores the raw document text.
    metadata_column : str
        Column name (jsonb) with date, author, priority, etc.
    top_k : int | None
        How many results to return. Defaults to TOP_K_SEARCH env var.

    Returns
    -------
    list[dict]
        Each dict has keys: content, metadata, score (cosine similarity).
    """
    from utils.db_utils import get_db_connection

    k = top_k or _TOP_K
    query_vector = embed_text(query_text)
    # Convert to PostgreSQL array literal
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

    sql = f"""
        SELECT
            {content_column}                                AS content,
            {metadata_column}                               AS metadata,
            1 - ({embedding_column} <=> '{vector_literal}') AS score
        FROM {table_name}
        ORDER BY {embedding_column} <=> '{vector_literal}'
        LIMIT %s;
    """

    conn = get_db_connection()
    if conn is None:
        print("vector_search: DB connection failed, returning empty list.")
        return []

    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (k,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        print(f"vector_search error: {exc}")
        return []
    finally:
        conn.close()


# =============================================================================
# PostgreSQL full-text (BM25-like) search
# =============================================================================

def bm25_search(
    query_text: str,
    table_name: str = "documents",
    tsvector_column: str = "tsv",
    content_column: str = "content",
    metadata_column: str = "meta",
    top_k: int | None = None,
    language: str = "english",
) -> list[dict[str, Any]]:
    """Full-text search using PostgreSQL's built-in tsvector / tsquery.

    Uses to_tsquery with OR (|) operator between individual words so that
    documents matching ANY query word are returned (ranked higher if more
    words match). This fixes the problem where plainto_tsquery required
    ALL words to be present, returning 0 results for multi-word queries.

    Parameters
    ----------
    query_text : str
        The plain-English search terms.
    table_name : str
        PostgreSQL table.
    tsvector_column : str
        Pre-computed tsvector column (indexed).
    content_column : str
        Raw document text column.
    metadata_column : str
        JSON metadata column.
    top_k : int | None
        Number of results.
    language : str
        PostgreSQL text-search language configuration.

    Returns
    -------
    list[dict]
        Each dict has keys: content, metadata, rank.
    """
    from utils.db_utils import get_db_connection

    k = top_k or _TOP_K

    # Build an OR-based tsquery: "word1 | word2 | word3"
    # This ensures documents containing ANY of the words will match,
    # and ts_rank_cd will rank them higher if more words match.
    import re
    # Tokenize: split on non-alphanumeric, filter short tokens
    raw_tokens = re.findall(r'[A-Za-z0-9]+', query_text)
    # Filter out very short tokens and common stopwords
    stopword_set = {
        'the', 'a', 'an', 'is', 'are', 'of', 'in', 'on', 'at', 'to',
        'for', 'and', 'or', 'who', 'what', 'how', 'which', 'that',
        'this', 'with', 'from', 'by', 'as', 'be', 'was', 'were',
        'has', 'have', 'had', 'do', 'does', 'did', 'will', 'would',
        'can', 'could', 'should', 'may', 'might', 'must', 'shall',
    }
    tokens = [t for t in raw_tokens if len(t) > 1 and t.lower() not in stopword_set]

    if not tokens:
        return []

    # Build OR query: token1 | token2 | token3
    tsquery_str = " | ".join(tokens)

    sql = f"""
        SELECT
            {content_column}                                           AS content,
            {metadata_column}                                          AS metadata,
            ts_rank_cd({tsvector_column}, to_tsquery(%s, %s))         AS rank
        FROM {table_name}
        WHERE {tsvector_column} @@ to_tsquery(%s, %s)
        ORDER BY rank DESC
        LIMIT %s;
    """

    conn = get_db_connection()
    if conn is None:
        print("bm25_search: DB connection failed, returning empty list.")
        return []

    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (language, tsquery_str, language, tsquery_str, k))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        print(f"bm25_search error: {exc}")
        return []
    finally:
        conn.close()


# =============================================================================
# Hybrid search (Reciprocal Rank Fusion)
# =============================================================================

def hybrid_search(
    query_text: str,
    table_name: str = "documents",
    top_k: int | None = None,
    rrf_k: int = 30,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
) -> list[dict[str, Any]]:
    """Combine vector search and BM25 search using Weighted Reciprocal Rank Fusion.

    RRF score = Σ weight_i * 1/(rrf_k + rank_i)   for each retrieval system i.

    By default: BM25 = 50% weight, Vector = 50% weight.
    Both keyword matching and semantic similarity contribute equally.

    Parameters
    ----------
    query_text : str
        The search query.
    table_name : str
        PostgreSQL table.
    top_k : int | None
        How many results to return after fusion.
    rrf_k : int
        RRF constant (30 gives better score differentiation than 60).
    vector_weight : float
        Weight for vector/semantic search (default 0.3 = 30%).
    bm25_weight : float
        Weight for BM25/keyword search (default 0.7 = 70%).

    Returns
    -------
    list[dict]
        Fused results sorted by RRF score, each with keys:
        content, metadata, rrf_score.
    """
    k = top_k or _TOP_K

    # Fetch more candidates from each system so fusion has enough to work with
    vec_results = vector_search(query_text, table_name=table_name, top_k=k * 3)
    bm25_results = bm25_search(query_text, table_name=table_name, top_k=k * 3)

    # Build RRF score map keyed by content (use content as surrogate ID)
    scores: dict[str, dict[str, Any]] = {}

    # Vector search contribution (70% weight)
    # Skip duplicates within the same system — only count first occurrence
    seen_vec: set[str] = set()
    for rank, row in enumerate(vec_results, start=1):
        key = row.get("content", "")
        if key in seen_vec:
            continue  # Don't double-count duplicates
        seen_vec.add(key)
        if key not in scores:
            scores[key] = {"content": key, "metadata": row.get("metadata"), "rrf_score": 0.0}
        scores[key]["rrf_score"] += vector_weight * (1.0 / (rrf_k + rank))

    # BM25 search contribution (30% weight)
    # Skip duplicates within the same system — only count first occurrence
    seen_bm25: set[str] = set()
    for rank, row in enumerate(bm25_results, start=1):
        key = row.get("content", "")
        if key in seen_bm25:
            continue  # Don't double-count duplicates
        seen_bm25.add(key)
        if key not in scores:
            scores[key] = {"content": key, "metadata": row.get("metadata"), "rrf_score": 0.0}
        scores[key]["rrf_score"] += bm25_weight * (1.0 / (rrf_k + rank))

    fused = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return fused[:k]


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    test_query = "কম্পিউটার বিজ্ঞান বিভাগের প্রধান"

    print("Testing hybrid_search...")
    results = hybrid_search(test_query)
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Score: {r.get('rrf_score', 0):.4f}")
        print(f"    Content: {str(r.get('content', ''))[:120]}")
        print(f"    Meta   : {r.get('metadata')}")
