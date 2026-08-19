"""
Admin Panel service layer
=========================

Wraps the existing Cnpi_RAG embedding + database utilities so the admin
panel can:

  * semantic_search(query, top_k)  -> embed the question and run pgvector
    cosine search on the ``documents`` table, returning chunk_id, doc_id,
    content, score, doc_type, topic, department, meta.

  * get_document(doc_id=None, chunk_id=None) -> fetch a single row by
    either key (used to pre-fill the update form).

  * update_document(doc_id=None, chunk_id=None, content=None,
                    doc_type=None, topic=None, department=None,
                    regenerate_embedding=True) -> UPDATE the row.  When
    content changes (or regenerate_embedding is forced) a fresh embedding
    vector is generated via embed_text() and written back.

  * document_stats() -> quick counts for the dashboard.

All SQL uses psycopg2 with parameterised queries; the vector literal is
built as a pgvector string ``[v1,v2,...]`` and cast with ``::vector``.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make Cnpi_RAG importable from the cnpi_api Django app
# ---------------------------------------------------------------------------
_CNPI_RAG_ROOT = Path(__file__).resolve().parent.parent.parent / "Cnpi_RAG"
if str(_CNPI_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(_CNPI_RAG_ROOT))

TABLE = "public.documents"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vec_to_pg_literal(vec: list[float]) -> str:
    """Convert a float list to a PostgreSQL pgvector literal ``[a,b,c]``."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def _row_to_dict(row) -> dict[str, Any]:
    """Normalise a RealDictRow into a plain JSON-safe dict."""
    if row is None:
        return None
    d = dict(row)
    # meta is jsonb -> already dict-like, but keep it serialisable
    if "meta" in d and not isinstance(d["meta"], (dict, list, str, type(None))):
        d["meta"] = json.dumps(d["meta"], ensure_ascii=False)
    return d


# ---------------------------------------------------------------------------
# Connection (reuse Cnpi_RAG db_utils so DATABASE_URL / SSL is honoured)
# ---------------------------------------------------------------------------

def _get_conn():
    from utils.db_utils import get_db_connection  # noqa: WPS433

    # ★ Admin panel needs write access to INSERT/UPDATE documents and notices
    conn = get_db_connection(allow_write=True)
    if conn is None:
        raise RuntimeError("Could not connect to the database. Check DATABASE_URL / DB_* env vars.")
    return conn


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def semantic_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Embed the question and run pgvector cosine similarity search.

    Returns a list of dicts (best match first) with keys:
        doc_id, chunk_id, content, doc_type, topic, department, meta, score
    """
    from utils.embedding_utils import embed_text  # noqa: WPS433

    query = (query or "").strip()
    if not query:
        return []

    top_k = max(1, min(int(top_k or 5), 50))

    query_vector = embed_text(query)
    vector_literal = _vec_to_pg_literal(query_vector)

    sql = f"""
        SELECT
            doc_id,
            chunk_id,
            content,
            doc_type,
            topic,
            department,
            meta,
            1 - (embedding <=> %s::vector) AS score
        FROM {TABLE}
        ORDER BY embedding <=> %s::vector, created_at DESC
        LIMIT %s;
    """

    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (vector_literal, vector_literal, top_k))
            rows = cur.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fetch a single document
# ---------------------------------------------------------------------------

def get_document(*, doc_id: int | str | None = None, chunk_id: str | None = None) -> dict[str, Any] | None:
    """Return one document row by doc_id or chunk_id (chunk_id takes priority)."""
    if not doc_id and not chunk_id:
        return None

    if chunk_id:
        sql = f"""
            SELECT doc_id, chunk_id, content, doc_type, topic, department,
                   meta, source_file, created_at, updated_at
            FROM {TABLE}
            WHERE chunk_id = %s
            LIMIT 1;
        """
        params: tuple = (chunk_id,)
    else:
        sql = f"""
            SELECT doc_id, chunk_id, content, doc_type, topic, department,
                   meta, source_file, created_at, updated_at
            FROM {TABLE}
            WHERE doc_id = %s
            LIMIT 1;
        """
        try:
            params = (int(doc_id),)
        except (TypeError, ValueError):
            return None

    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Create (insert a brand-new document)
# ---------------------------------------------------------------------------

_VALID_DEPTS = {"CST", "ET", "ENT", "RAC", "FT", "MT", "Non-Tech", "General"}


def create_document(
    *,
    chunk_id: str,
    content: str,
    doc_type: str | None = "general",
    topic: str | None = None,
    department: str | None = None,
    meta: dict | str | None = None,
    source_file: str | None = "admin_panel",
) -> dict[str, Any]:
    """Insert a new document row with an auto-generated embedding.

    - chunk_id is required and must be unique (UNIQUE constraint).
    - content is required and must be > 10 chars (table CHECK constraint).
    - department, if provided, must be one of the valid short codes.
    - meta may be a dict or a JSON string (defaults to {}).

    Returns {created, doc_id, chunk_id, embedding_generated, document} or {error}.
    If the chunk_id already exists, returns an error pointing to update instead.
    """
    from utils.embedding_utils import embed_text  # noqa: WPS433

    new_doc_type = (doc_type or "general").strip() or "general"

    # For notices, chunk_id is auto-generated after notice insert (notice-{notice_id})
    # So we skip chunk_id validation for notices here; it will be set later.
    _is_notice = new_doc_type.lower() == "notices"

    new_chunk_id = (chunk_id or "").strip()
    if not _is_notice:
        if not new_chunk_id:
            return {"error": "chunk_id is required."}
        if len(new_chunk_id) > 200:
            return {"error": "chunk_id must be at most 200 characters."}

    new_content = (content or "").strip()
    if len(new_content) < 11:
        return {"error": "content is required and must be at least 11 characters."}

    new_topic = (topic or "").strip() or None
    new_dept = (department or "").strip() or None
    if new_dept and new_dept not in _VALID_DEPTS:
        return {
            "error": f"Invalid department '{new_dept}'. Valid: {sorted(_VALID_DEPTS)}",
        }

    # meta → JSON string
    if meta is None or meta == "":
        meta_json = "{}"
    elif isinstance(meta, str):
        try:
            json.loads(meta)  # validate
            meta_json = meta
        except json.JSONDecodeError as exc:
            return {"error": f"meta is not valid JSON: {exc}"}
    else:
        meta_json = json.dumps(meta, ensure_ascii=False)

    new_source = (source_file or "").strip() or None

    # ---- check for existing chunk_id (only for non-notices) ----
    if not _is_notice and new_chunk_id:
        existing = get_document(chunk_id=new_chunk_id)
        if existing is not None:
            return {
                "error": f"chunk_id '{new_chunk_id}' already exists (doc_id={existing.get('doc_id')}). Use the Update tab instead.",
            }

    # ================================================================
    # PRE-PROCESSING PIPELINE (runs before embedding is generated)
    # ================================================================

    # Step 1 — Translate Bengali/mixed content → English
    # ----------------------------------------------------------------
    original_content = new_content
    translation_performed = False
    try:
        from nodes.doc_translator import translate_to_english, _should_translate  # noqa: WPS433
        if _should_translate(new_content):
            logger.info("create_document: Bengali/Banglish detected – running translation pipeline.")
            translated_content = translate_to_english(new_content)
            if translated_content and translated_content != new_content:
                new_content = translated_content
                translation_performed = True
                logger.info("create_document: Translation done (%d → %d chars).",
                            len(original_content), len(new_content))
            else:
                logger.info("create_document: Translation returned same text – using original.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_document: Translation step failed (%s); using original content.", exc)

    # Step 2 — Entity normalisation (e.g. "computer" → "CST", "রুটিন" → "Routine")
    # ----------------------------------------------------------------
    try:
        from nodes.entity_normalizer import normalize_entities, ALIAS_TABLE  # noqa: WPS433
        normalized = normalize_entities(new_content, ALIAS_TABLE)
        if normalized and normalized != new_content:
            logger.info("create_document: Entity normalization modified content.")
            new_content = normalized
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_document: Entity normalization failed (%s); skipping.", exc)

    # Step 3 — Calculate context_added_date and context_added_time (needed for temporal analysis)
    # ----------------------------------------------------------------
    now_utc = datetime.now(tz=timezone.utc)
    # Convert to Bangladesh Standard Time (UTC+6)
    from datetime import timedelta  # noqa: WPS433
    bst_offset = timedelta(hours=6)
    now_bst = now_utc + bst_offset
    context_added_date = now_bst.strftime("%Y-%m-%d")
    context_added_time = now_bst.strftime("%H:%M:%S")

    # Step 4 — Temporal Analysis (extract dates, events, validity periods)
    # ----------------------------------------------------------------
    # ★ Temporal analysis JSON will be stored ONLY in the temporal_analysis column
    # ★ NOT prepended to content anymore
    temporal_analysis_json = None
    try:
        from nodes.temporal_analyzer import analyze_temporal_context  # noqa: WPS433
        logger.info("create_document: Running temporal analysis...")
        temporal_data = analyze_temporal_context(new_content, notice_date=context_added_date)
        if temporal_data and isinstance(temporal_data, dict):
            temporal_analysis_json = json.dumps(temporal_data, ensure_ascii=False)
            logger.info("create_document: Temporal analysis completed successfully.")
            logger.info(f"create_document: Temporal data - valid_until: {temporal_data.get('valid_until')}")
        else:
            logger.warning("create_document: Temporal analysis returned empty/invalid data.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_document: Temporal analysis failed (%s); skipping.", exc)

    # Step 5 — Append metadata to meta dict
    # ----------------------------------------------------------------

    # Step 5 continued — Merge into the existing meta dict
    try:
        existing_meta: dict = json.loads(meta_json) if meta_json and meta_json != "{}" else {}
    except (json.JSONDecodeError, TypeError):
        existing_meta = {}

    existing_meta["context_added_date"] = context_added_date
    existing_meta["context_added_time"] = context_added_time
    existing_meta["translation_performed"] = translation_performed
    if translation_performed:
        existing_meta["original_content_lang"] = "Bengali/mixed"

    meta_json = json.dumps(existing_meta, ensure_ascii=False)

    # Prepend the date/time stamp and metadata as a visible header in the content itself
    # so that retrieval context automatically carries this provenance info.
    timestamp_header = (
        f"[context_added_date: {context_added_date} | "
        f"context_added_time: {context_added_time} BST]\n"
    )
    
    # Add Doc Type, Department, and Topic after the timestamp
    metadata_lines = []
    if new_doc_type:
        metadata_lines.append(f"Doc Type: {new_doc_type}")
    if new_dept:
        metadata_lines.append(f"Department: {new_dept}")
    if new_topic:
        metadata_lines.append(f"Topic: {new_topic}")
    
    metadata_header = "\n".join(metadata_lines) + "\n\n" if metadata_lines else "\n"
    
    # ★ NO temporal analysis text in content - only timestamp + metadata + original content
    new_content = timestamp_header + metadata_header + new_content.lstrip()

    # ================================================================
    # END PRE-PROCESSING PIPELINE
    # ================================================================

    # ---- generate embedding ----
    try:
        vec = embed_text(new_content)
        vec_literal = _vec_to_pg_literal(vec)
    except Exception as exc:
        logger.exception("create_document embedding failed")
        return {"error": f"Embedding generation failed: {exc}"}

    # ================================================================
    # SPECIAL CASE: Insert into notices table if doc_type is 'notices'
    # ================================================================
    if new_doc_type.lower() == "notices":
        conn = _get_conn()
        try:
            # Insert into notices table first
            institution_id = 1  # Default CNPI institution
            category = new_dept if new_dept else "General"
            title_bn = new_topic if new_topic else "নতুন নোটিশ"
            
            # Use processed content (timestamp + metadata + English/Bengali)
            notice_content = new_content
            
            # Prepare SQL based on whether temporal_analysis exists
            if temporal_analysis_json:
                sql_notices = """
                    INSERT INTO public.notices
                        (institution_id, category, title_bn, content_bn, temporal_analysis, created_at)
                    VALUES
                        (%s, %s, %s, %s, %s::jsonb, NOW())
                    RETURNING notice_id;
                """
                params_notices = (institution_id, category, title_bn, notice_content, temporal_analysis_json)
            else:
                # If temporal_analysis is NULL, insert without it
                sql_notices = """
                    INSERT INTO public.notices
                        (institution_id, category, title_bn, content_bn, created_at)
                    VALUES
                        (%s, %s, %s, %s, NOW())
                    RETURNING notice_id;
                """
                params_notices = (institution_id, category, title_bn, notice_content)
            
            logger.info(f"Inserting into notices table: category={category}, title={title_bn[:30]}...")
            
            with conn.cursor() as cur:
                cur.execute(sql_notices, params_notices)
                notice_returned = cur.fetchone()
                conn.commit()
            
            if not notice_returned:
                conn.close()
                logger.error("notices insert returned no row")
                return {"error": "Insert into notices table returned no row."}
            
            notice_id = notice_returned[0]
            # Auto-generate chunk_id as notice-{notice_id}
            new_chunk_id = f"notice-{notice_id}"
            logger.info(f"✅ Successfully inserted into notices table with notice_id={notice_id}, auto chunk_id={new_chunk_id}")
            
            # Insert into documents table for search purposes.
            # Use ON CONFLICT DO UPDATE so that if this chunk_id somehow already
            # exists (e.g. a previous failed attempt left a stale row), we
            # overwrite it with the fresh content + embedding instead of failing.
            sql_documents = f"""
                INSERT INTO {TABLE}
                    (chunk_id, content, doc_type, topic, department, embedding, meta, source_file, temporal_analysis)
                VALUES
                    (%s, %s, %s, %s, %s, %s::vector, %s::jsonb, %s, %s::jsonb)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content            = EXCLUDED.content,
                    doc_type           = EXCLUDED.doc_type,
                    topic              = EXCLUDED.topic,
                    department         = EXCLUDED.department,
                    embedding          = EXCLUDED.embedding,
                    meta               = EXCLUDED.meta,
                    source_file        = EXCLUDED.source_file,
                    temporal_analysis  = EXCLUDED.temporal_analysis
                RETURNING doc_id, chunk_id;
            """
            params_documents = (
                new_chunk_id,
                new_content,
                new_doc_type,
                new_topic,
                new_dept,
                vec_literal,
                meta_json,
                new_source,
                temporal_analysis_json,
            )
            
            with conn.cursor() as cur:
                cur.execute(sql_documents, params_documents)
                doc_returned = cur.fetchone()
                conn.commit()
            
            if not doc_returned:
                conn.close()
                return {"error": "Insert into documents table returned no row."}
            
            doc = get_document(doc_id=doc_returned[0])
            conn.close()
            
            return {
                "created": True,
                "doc_id": doc_returned[0],
                "chunk_id": doc_returned[1],
                "notice_id": notice_id,
                "inserted_into_notices": True,
                "embedding_generated": True,
                "translation_performed": translation_performed,
                "temporal_analysis_performed": temporal_analysis_json is not None,
                "context_added_date": context_added_date,
                "context_added_time": context_added_time,
                "document": doc,
            }
        except Exception as exc:
            conn.rollback()
            conn.close()
            logger.exception("create_document failed for notices")
            return {"error": f"Database insert failed: {exc}"}
    
    # ================================================================
    # NORMAL CASE: Insert only into documents table
    # ================================================================
    sql = f"""
        INSERT INTO {TABLE}
            (chunk_id, content, doc_type, topic, department, embedding, meta, source_file, temporal_analysis)
        VALUES
            (%s, %s, %s, %s, %s, %s::vector, %s::jsonb, %s, %s::jsonb)
        RETURNING doc_id, chunk_id;
    """
    params = (
        new_chunk_id,
        new_content,
        new_doc_type,
        new_topic,
        new_dept,
        vec_literal,
        meta_json,
        new_source,
        temporal_analysis_json,
    )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            returned = cur.fetchone()
            conn.commit()
        if not returned:
            return {"error": "Insert returned no row."}
        doc = get_document(doc_id=returned[0])
        return {
            "created": True,
            "doc_id": returned[0],
            "chunk_id": returned[1],
            "embedding_generated": True,
            "translation_performed": translation_performed,
            "temporal_analysis_performed": temporal_analysis_json is not None,
            "context_added_date": context_added_date,
            "context_added_time": context_added_time,
            "document": doc,
        }
    except Exception as exc:
        conn.rollback()
        logger.exception("create_document failed")
        return {"error": f"Database insert failed: {exc}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def update_document(
    *,
    doc_id: int | str | None = None,
    chunk_id: str | None = None,
    content: str | None = None,
    doc_type: str | None = None,
    topic: str | None = None,
    department: str | None = None,
    regenerate_embedding: bool = True,
) -> dict[str, Any]:
    """Update a documents row by doc_id or chunk_id.

    - content is required and must be > 10 chars (table CHECK constraint).
    - If regenerate_embedding is True (default), a new embedding is generated
      from the new content and written to the ``embedding`` column.
    - department, if provided, must be one of the valid short codes.

    Returns a dict describing the result: {updated, doc_id, chunk_id,
    embedding_regenerated, before, after} or {error}.
    """
    from utils.embedding_utils import embed_text  # noqa: WPS433

    # ---- resolve identifier ----
    if not doc_id and not chunk_id:
        return {"error": "Provide either doc_id or chunk_id."}

    if chunk_id:
        where_clause = "chunk_id = %s"
        where_params: tuple = (chunk_id,)
    else:
        try:
            doc_id_int = int(doc_id)
        except (TypeError, ValueError):
            return {"error": f"doc_id must be an integer, got: {doc_id!r}"}
        where_clause = "doc_id = %s"
        where_params = (doc_id_int,)

    # ---- validate inputs ----
    new_content = (content or "").strip()
    if len(new_content) < 11:
        return {"error": "content is required and must be at least 11 characters."}

    new_dept = (department or "").strip() or None
    if new_dept and new_dept not in _VALID_DEPTS:
        return {
            "error": f"Invalid department '{new_dept}'. Valid: {sorted(_VALID_DEPTS)}",
        }

    new_doc_type = (doc_type or "").strip() or None
    new_topic = (topic or "").strip() or None

    # ---- fetch existing (so we can report before/after) ----
    before = get_document(doc_id=doc_id, chunk_id=chunk_id)
    if before is None:
        return {"error": f"Document not found (doc_id={doc_id}, chunk_id={chunk_id})."}

    # ---- build UPDATE ----
    sets: list[str] = ["content = %s"]
    values: list[Any] = [new_content]

    if new_doc_type is not None:
        sets.append("doc_type = %s")
        values.append(new_doc_type)
    if new_topic is not None:
        sets.append("topic = %s")
        values.append(new_topic if new_topic != "" else None)
    if new_dept is not None:
        sets.append("department = %s")
        values.append(new_dept)

    embedding_regenerated = False
    if regenerate_embedding:
        vec = embed_text(new_content)
        vec_literal = _vec_to_pg_literal(vec)
        sets.append("embedding = %s::vector")
        values.append(vec_literal)
        embedding_regenerated = True

    sets.append("updated_at = NOW()")

    sql = f"UPDATE {TABLE} SET {', '.join(sets)} WHERE {where_clause} RETURNING doc_id, chunk_id;"
    params = tuple(values) + where_params

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            returned = cur.fetchone()
            conn.commit()
        if not returned:
            return {"error": "No row was updated (row may have been deleted)."}
        after = get_document(doc_id=returned[0], chunk_id=None)
        return {
            "updated": True,
            "doc_id": returned[0],
            "chunk_id": returned[1],
            "embedding_regenerated": embedding_regenerated,
            "before": before,
            "after": after,
        }
    except Exception as exc:
        conn.rollback()
        logger.exception("update_document failed")
        return {"error": f"Database update failed: {exc}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Captain CRUD
# ---------------------------------------------------------------------------

_VALID_DEPARTMENTS = ["CST", "ET", "ENT", "RAC", "FT", "MT"]
_VALID_SHIFTS = ["Day", "Morning"]
_VALID_SEMESTERS = list(range(1, 8))  # 1–7
_VALID_RANKS = [1, 2]                 # 1 = 1st Captain, 2 = 2nd Captain


def create_captain(
    *,
    department: str,
    shift: str,
    semester: int,
    captain_name: str,
    captain_rank: int = 1,
    student_id: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    session_year: str | None = None,
) -> dict[str, Any]:
    """Insert a new active captain into class_captains table.

    captain_rank=1 → 1st Captain, captain_rank=2 → 2nd Captain.

    Before inserting, deactivates any existing active captain with the same
    department + shift + semester + rank combination so there is at most one
    active 1st-captain and one active 2nd-captain per class slot.

    Returns {created, captain_id, ...} or {error}.
    """
    # ---- validate ----
    dept = (department or "").strip()
    if dept not in _VALID_DEPARTMENTS:
        return {"error": f"Invalid department '{dept}'. Valid: {_VALID_DEPARTMENTS}"}

    sh = (shift or "").strip()
    if sh not in _VALID_SHIFTS:
        return {"error": f"Invalid shift '{sh}'. Valid: {_VALID_SHIFTS}"}

    try:
        sem = int(semester)
    except (TypeError, ValueError):
        return {"error": "semester must be an integer between 1 and 7."}
    if sem not in _VALID_SEMESTERS:
        return {"error": f"semester must be between 1 and 7, got {sem}."}

    try:
        rank = int(captain_rank)
    except (TypeError, ValueError):
        rank = 1
    if rank not in _VALID_RANKS:
        return {"error": "captain_rank must be 1 (1st Captain) or 2 (2nd Captain)."}

    name = (captain_name or "").strip()
    if not name:
        return {"error": "captain_name is required."}
    if len(name) > 100:
        return {"error": "captain_name must be at most 100 characters."}

    sid = (student_id or "").strip() or None
    ph = (phone or "").strip() or None
    em = (email or "").strip() or None
    sy = (session_year or "").strip() or None

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Deactivate any existing active captain for same slot + rank
            cur.execute(
                """
                UPDATE public.class_captains
                   SET is_active = FALSE, updated_at = NOW()
                 WHERE institution_id = 1
                   AND department = %s
                   AND shift = %s
                   AND semester = %s
                   AND captain_rank = %s
                   AND is_active = TRUE
                """,
                (dept, sh, sem, rank),
            )

            # Insert new captain
            cur.execute(
                """
                INSERT INTO public.class_captains
                    (institution_id, department, shift, semester,
                     captain_rank, captain_name, student_id, phone, email,
                     session_year, is_active, created_at, updated_at)
                VALUES
                    (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                RETURNING captain_id;
                """,
                (dept, sh, sem, rank, name, sid, ph, em, sy),
            )
            row = cur.fetchone()
            conn.commit()

        if not row:
            return {"error": "Insert returned no row."}

        captain = get_captain(captain_id=row[0])
        return {"created": True, "captain_id": row[0], "captain": captain}

    except Exception as exc:
        conn.rollback()
        logger.exception("create_captain failed")
        return {"error": f"Database insert failed: {exc}"}
    finally:
        conn.close()


def get_captain(*, captain_id: int | None = None) -> dict[str, Any] | None:
    """Fetch a single captain row by captain_id."""
    if captain_id is None:
        return None
    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT captain_id, institution_id, department, shift, semester,
                       captain_rank, captain_name, student_id, phone, email,
                       session_year, is_active, created_at, updated_at
                  FROM public.class_captains
                 WHERE captain_id = %s
                """,
                (captain_id,),
            )
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_captains(
    *,
    department: str | None = None,
    shift: str | None = None,
    semester: int | None = None,
    captain_rank: int | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """List captains with optional filters."""
    conditions = ["institution_id = 1"]
    params: list[Any] = []

    if active_only:
        conditions.append("is_active = TRUE")
    if department:
        conditions.append("department = %s")
        params.append(department.strip())
    if shift:
        conditions.append("shift = %s")
        params.append(shift.strip())
    if semester is not None:
        conditions.append("semester = %s")
        params.append(int(semester))
    if captain_rank is not None:
        conditions.append("captain_rank = %s")
        params.append(int(captain_rank))

    where = " AND ".join(conditions)
    sql = f"""
        SELECT captain_id, department, shift, semester,
               captain_rank, captain_name, student_id, phone, email,
               session_year, is_active, created_at, updated_at
          FROM public.class_captains
         WHERE {where}
         ORDER BY department, shift, semester, captain_rank, is_active DESC, created_at DESC;
    """

    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_captain(
    *,
    captain_id: int,
    captain_name: str | None = None,
    student_id: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    session_year: str | None = None,
) -> dict[str, Any]:
    """Update editable fields of an existing captain row."""
    sets: list[str] = []
    values: list[Any] = []

    if captain_name is not None:
        n = captain_name.strip()
        if not n:
            return {"error": "captain_name cannot be empty."}
        sets.append("captain_name = %s")
        values.append(n)
    if student_id is not None:
        sets.append("student_id = %s")
        values.append(student_id.strip() or None)
    if phone is not None:
        sets.append("phone = %s")
        values.append(phone.strip() or None)
    if email is not None:
        sets.append("email = %s")
        values.append(email.strip() or None)
    if session_year is not None:
        sets.append("session_year = %s")
        values.append(session_year.strip() or None)

    if not sets:
        return {"error": "No fields provided to update."}

    sets.append("updated_at = NOW()")
    values.append(int(captain_id))

    sql = f"""
        UPDATE public.class_captains
           SET {', '.join(sets)}
         WHERE captain_id = %s
         RETURNING captain_id;
    """

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            row = cur.fetchone()
            conn.commit()
        if not row:
            return {"error": f"captain_id={captain_id} not found."}
        captain = get_captain(captain_id=row[0])
        return {"updated": True, "captain_id": row[0], "captain": captain}
    except Exception as exc:
        conn.rollback()
        logger.exception("update_captain failed")
        return {"error": f"Database update failed: {exc}"}
    finally:
        conn.close()


def deactivate_captain(*, captain_id: int) -> dict[str, Any]:
    """Set is_active=FALSE for a captain."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.class_captains
                   SET is_active = FALSE, updated_at = NOW()
                 WHERE captain_id = %s
                 RETURNING captain_id;
                """,
                (int(captain_id),),
            )
            row = cur.fetchone()
            conn.commit()
        if not row:
            return {"error": f"captain_id={captain_id} not found."}
        return {"deactivated": True, "captain_id": row[0]}
    except Exception as exc:
        conn.rollback()
        logger.exception("deactivate_captain failed")
        return {"error": f"Database update failed: {exc}"}
    finally:
        conn.close()


def captain_stats() -> dict[str, Any]:
    """Return captain counts grouped by department and shift."""
    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT department, shift,
                       COUNT(*) FILTER (WHERE is_active) AS active_count,
                       COUNT(*) AS total_count
                  FROM public.class_captains
                 WHERE institution_id = 1
                 GROUP BY department, shift
                 ORDER BY department, shift;
                """
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM public.class_captains WHERE institution_id = 1 AND is_active = TRUE"
            )
            total_active = cur.fetchone()["cnt"]
        return {
            "total_active": total_active,
            "by_dept_shift": [dict(r) for r in rows],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def document_stats() -> dict[str, Any]:
    """Return basic counts for the dashboard."""
    sql_total = f"SELECT COUNT(*) AS cnt FROM {TABLE}"
    sql_by_type = f"""
        SELECT doc_type, COUNT(*) AS cnt
        FROM {TABLE}
        GROUP BY doc_type
        ORDER BY cnt DESC
    """
    sql_by_dept = f"""
        SELECT COALESCE(department, '(NULL)') AS department, COUNT(*) AS cnt
        FROM {TABLE}
        GROUP BY department
        ORDER BY cnt DESC
    """

    conn = _get_conn()
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql_total)
            total = cur.fetchone()["cnt"]
            cur.execute(sql_by_type)
            by_type = [dict(r) for r in cur.fetchall()]
            cur.execute(sql_by_dept)
            by_dept = [dict(r) for r in cur.fetchall()]
        return {"total": total, "by_doc_type": by_type, "by_department": by_dept}
    finally:
        conn.close()
