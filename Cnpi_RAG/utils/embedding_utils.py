"""
Embedding & BM25 Search Utilities
===================================

Provides:
  - get_embedding_model()  : SentenceTransformer singleton (local mode)
  - embed_text(text)       : returns list[float] (local OR HF Inference API)
  - embed_batch(texts)     : batch embed (local OR HF Inference API)
  - vector_search(...)     : cosine-similarity search via PostgreSQL pgvector
  - bm25_search(...)       : full-text search via PostgreSQL tsvector/tsquery
  - hybrid_search(...)     : combines vector + BM25 results (RRF fusion)

Two backends are supported, selected by EMBEDDING_PROVIDER env var:
  - "local"  → SentenceTransformer loaded in-process (needs ~2GB RAM)
  - "hf_api" → HuggingFace Inference API (no model download, ~0 RAM)

Environment variables used (from .env):
  EMBEDDING_PROVIDER  = hf_api | local   (default: local)
  EMBEDDING_MODEL     = BAAI/bge-m3       (model id, used by both backends)
  EMBEDDING_DIMENSION = 1024             (vector dim, MUST match DB column)
  HF_TOKEN            = hf_xxx...         (required for hf_api mode)
  TOP_K_SEARCH        = 5
"""

import os
import time
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

load_dotenv()

_EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local").lower()
_EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
_EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
_TOP_K: int = int(os.getenv("TOP_K_SEARCH", "5"))
_HF_TOKEN: str = os.getenv("HF_TOKEN", "")

# METRIC_THRESHOLD controls the embedding vs BM25 weight ratio in hybrid_search.
#   METRIC_THRESHOLD = embedding (vector) weight  (0.0 – 1.0)
#   bm25_weight      = 1.0 - METRIC_THRESHOLD
# Example: METRIC_THRESHOLD=0.20 → 20% embedding, 80% BM25
_METRIC_THRESHOLD: float = float(os.getenv("METRIC_THRESHOLD", "0.5"))


# =============================================================================
# Local embedding model singleton
# =============================================================================

def get_embedding_model():
    """Return a lazily-created SentenceTransformer singleton.

    Only used when EMBEDDING_PROVIDER=local.  Keeping a single instance
    avoids reloading the model weights on every graph invocation.
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


# =============================================================================
# HuggingFace Inference API embedding (via huggingface_hub.InferenceClient)
# =============================================================================

def _get_hf_client():
    """Return a cached InferenceClient (router.huggingface.co endpoint)."""
    if not hasattr(_get_hf_client, "_client"):
        if not _HF_TOKEN:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=hf_api requires HF_TOKEN. "
                "Get one at https://huggingface.co/settings/tokens (read access)."
            )
        from huggingface_hub import InferenceClient
        _get_hf_client._client = InferenceClient(
            model=_EMBEDDING_MODEL_NAME,
            token=_HF_TOKEN,
        )
        print(f"✓ HF Inference API client ready: {_EMBEDDING_MODEL_NAME}")
    return _get_hf_client._client


def _hf_embed_batch(texts: list[str]) -> list[list[float]]:
    """Call HF Inference API feature-extraction for a batch via InferenceClient.

    Uses huggingface_hub.InferenceClient which hits router.huggingface.co
    (the api-inference.huggingface.co subdomain was deprecated).  Returns
    L2-normalized sentence vectors (one per input text).
    """
    client = _get_hf_client()

    # Retry on cold-start — the model may be loading on first call.
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            result = client.feature_extraction(text=texts, normalize=True)
            import numpy as np

            arr = np.asarray(result)
            # bge-m3 returns shape (n, 1024) when normalize=True; but be
            # defensive and flatten/mean-pool token vectors if needed.
            if arr.ndim == 3:
                # (n, tokens, dim) → mean-pool over tokens
                arr = arr.mean(axis=1)
            elif arr.ndim == 2 and arr.shape[0] == len(texts):
                pass  # already (n, dim)
            elif arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return [v.tolist() for v in arr]
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"HF Inference API failed after retries: {last_exc}")


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured backend.

    Returns list of float vectors, each L2-normalized.
    """
    if not texts:
        return []
    if _EMBEDDING_PROVIDER == "hf_api":
        return _hf_embed_batch(texts)
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [v.tolist() for v in vectors]


def embed_text(text: str) -> list[float]:
    """Convert a text string into a dense embedding vector.

    Uses the backend selected by EMBEDDING_PROVIDER:
      - local  → in-process SentenceTransformer
      - hf_api → HuggingFace Inference API (no model download)
    """
    if _EMBEDDING_PROVIDER == "hf_api":
        return _hf_embed_batch([text])[0]
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
        WHERE (
            temporal_analysis IS NULL
            OR temporal_analysis->>'expiration_date' IS NULL
            OR (temporal_analysis->>'expiration_date')::date >= CURRENT_DATE
        )
        ORDER BY {embedding_column} <=> '{vector_literal}', created_at DESC
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
          AND (
            temporal_analysis IS NULL
            OR temporal_analysis->>'expiration_date' IS NULL
            OR (temporal_analysis->>'expiration_date')::date >= CURRENT_DATE
          )
        ORDER BY rank DESC, created_at DESC
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
    vector_weight: float | None = None,
    bm25_weight: float | None = None,
) -> list[dict[str, Any]]:
    """Combine vector search and BM25 search using Weighted Reciprocal Rank Fusion.

    RRF score = Σ weight_i * 1/(rrf_k + rank_i)   for each retrieval system i.

    The embedding (vector) vs BM25 weight ratio is controlled by the
    METRIC_THRESHOLD environment variable:

        METRIC_THRESHOLD = embedding (vector) weight  (range: 0.0 – 1.0)
        bm25_weight      = 1.0 - METRIC_THRESHOLD

    Example:
        METRIC_THRESHOLD=0.20  →  20% embedding, 80% BM25
        METRIC_THRESHOLD=0.55  →  55% embedding, 45% BM25

    If METRIC_THRESHOLD is not set, defaults to 0.5 (equal weight).

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
    vector_weight : float | None
        Override for vector/semantic weight. If None, uses METRIC_THRESHOLD.
    bm25_weight : float | None
        Override for BM25/keyword weight. If None, uses 1 - METRIC_THRESHOLD.

    Returns
    -------
    list[dict]
        Fused results sorted by RRF score, each with keys:
        content, metadata, rrf_score.
    """
    k = top_k or _TOP_K

    # Resolve weights from METRIC_THRESHOLD env var unless explicitly overridden
    if vector_weight is None:
        vector_weight = _METRIC_THRESHOLD
    if bm25_weight is None:
        bm25_weight = 1.0 - _METRIC_THRESHOLD

    print(
        f"[hybrid_search] weights → embedding: {vector_weight:.2f}, "
        f"bm25: {bm25_weight:.2f} (METRIC_THRESHOLD={_METRIC_THRESHOLD:.2f})"
    )

    # ⚡ PARALLEL EXECUTION: Fetch embedding and BM25 results simultaneously
    # This reduces latency by ~40-50% compared to sequential execution
    vec_results = []
    bm25_results = []
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both searches in parallel with keyword arguments
        future_vec = executor.submit(vector_search, query_text=query_text, table_name=table_name, top_k=k * 3)
        future_bm25 = executor.submit(bm25_search, query_text=query_text, table_name=table_name, top_k=k * 3)
        
        # Collect results as they complete
        for future in as_completed([future_vec, future_bm25]):
            try:
                result = future.result()
                if future == future_vec:
                    vec_results = result
                else:
                    bm25_results = result
            except Exception as exc:
                print(f"[hybrid_search] Parallel search error: {exc}")
                # Continue with empty results for failed search

    # Build RRF score map keyed by content (use content as surrogate ID)
    scores: dict[str, dict[str, Any]] = {}

    # Vector search contribution
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

    # BM25 search contribution
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
