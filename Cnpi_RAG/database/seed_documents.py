"""
========================================================
CNPI RAG — Document Seed Script
========================================================

এই script G:\\CNPIRAG_Backend\\Document_Translated\\
ফোল্ডারের সব JSON file পড়ে, প্রতিটি dictionary-কে
একটি chunk হিসেবে treat করে, embedding করে
documents table-এ upsert করে।

Usage:
    cd G:\\CNPI_Hybrid_RAG\\Cnpi_RAG
    python database\\seed_documents.py

Features:
    - প্রতিটি JSON file আলাদাভাবে process হয়
    - chunk_id conflict হলে ON CONFLICT DO UPDATE (safe re-run)
    - embedding batch করে করা হয় (memory efficient)
    - progress bar দেখায়
    - error হলে সেই chunk skip করে বাকিগুলো চালিয়ে যায়
    - শেষে summary দেখায়
"""

import json
import os
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# ─── Config ──────────────────────────────────────────────────
DOCS_DIR    = Path(r"G:\CNPIRAG_Backend\Document_Translated")
BATCH_SIZE  = 16   # একসাথে কতগুলো embed করা হবে (memory vs speed tradeoff)
TABLE       = "public.documents"

# department short_code valid values (documents table CHECK constraint)
VALID_DEPTS = {"CST", "ET", "ENT", "RAC", "FT", "MT", "Non-Tech", "General"}

# প্রতিটি JSON file-এর জন্য config:
# doc_type_default  → যদি item-এ doc_type না থাকে
# dept_field        → কোন field থেকে department নেওয়া হবে
# keep_as_meta      → এই fields meta JSONB-এ যাবে
FILE_CONFIG = {
    "academic_rules.json": {
        "doc_type_default": "academic_rules",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "administration_contacts.json": {
        "doc_type_default": "administration_contacts",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "all_labs_summary.json": {
        "doc_type_default": "all_labs_summary",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "total_labs", "language"],
    },
    "ci_list.json": {
        "doc_type_default": "ci_consolidated_list",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "total_ci", "language"],
    },
    "class_rutine.json": {
        "doc_type_default": "class_routine",
        "dept_field": "department",
        "keep_as_meta": ["semester", "session", "group", "day"],
    },
    "class_rutine_1st_shift.json": {
        "doc_type_default": "class_routine",
        "dept_field": "department",
        "keep_as_meta": ["semester", "session", "group", "day"],
    },
    "cnpi_total_summary.json": {
        "doc_type_default": "cnpi_aggregate_statistics",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "cst_class_routine_weekly_summary.json": {
        "doc_type_default": "weekly_routine_summary",
        "dept_field": "department_short",
        "keep_as_meta": ["semester", "semester_bn", "group", "shift", "session", "institution"],
    },
    "department_overview.json": {
        "doc_type_default": "department_overview",
        "dept_field": "department_short",
        "keep_as_meta": ["total_teachers", "total_labs", "institution", "language"],
    },
    "department_teacher_summary.json": {
        "doc_type_default": "department_teacher_summary",
        "dept_field": "department_short",
        "keep_as_meta": ["total_teachers", "institution", "language"],
    },
    "female_teachers_summary.json": {
        "doc_type_default": "female_teachers_summary",
        "dept_field": None,
        "keep_as_meta": ["total_female_teachers", "institution", "language"],
    },
    "Future_Development.json": {
        "doc_type_default": "institution_future_plan",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "key_personnel.json": {
        "doc_type_default": "key_personnel",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "labinfo.json": {
        "doc_type_default": "lab_info",
        "dept_field": "department",
        "keep_as_meta": ["total_labs", "labs"],
    },
    "lab_info_where.json": {
        "doc_type_default": "lab_location",
        "dept_field": None,          # metadata nested dict থেকে নেওয়া হবে
        "keep_as_meta": [],          # পুরো metadata field যাবে
    },
    "Mission_Vision.json": {
        "doc_type_default": "institution_policy",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "Overview.json": {
        "doc_type_default": "institution_details",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "part_time_teacher.json": {
        "doc_type_default": "teachers_info",
        "dept_field": "department",
        "keep_as_meta": ["name", "designation", "phone"],
    },
    "Recent_Development.json": {
        "doc_type_default": "institution_facilities",
        "dept_field": None,
        "keep_as_meta": ["institution", "institution_short", "language"],
    },
    "staff_by_category.json": {
        "doc_type_default": "staff_by_category",
        "dept_field": None,
        "keep_as_meta": ["category", "institution", "language"],
    },
    "staff_data.json": {
        "doc_type_default": "staff_info",
        "dept_field": "department",
        "keep_as_meta": ["name", "designation", "email", "phone"],
    },
    "teachers_data.json": {
        "doc_type_default": "teachers_info",
        "dept_field": "department",
        "keep_as_meta": ["name", "designation", "phone"],
    },
}


# ─── Helpers ──────────────────────────────────────────────────

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432"),
    )


def get_embedding_model():
    """SentenceTransformer singleton for BAAI/bge-m3."""
    if not hasattr(get_embedding_model, "_model"):
        from sentence_transformers import SentenceTransformer
        print("  Loading embedding model (first time only)...")
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        get_embedding_model._model = SentenceTransformer(model_name)
        print(f"  Model loaded: {model_name}")
    return get_embedding_model._model


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, returns list of float vectors."""
    model = get_embedding_model()
    # bge-m3 works well with normalize_embeddings=True for cosine similarity
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [v.tolist() for v in vectors]


def normalize_department(raw: str | None) -> str | None:
    """
    department field-কে valid short_code-এ normalize করে।
    Invalid হলে None return করে।
    """
    if not raw:
        return None
    raw = str(raw).strip()

    # direct match
    if raw in VALID_DEPTS:
        return raw

    # common variations → normalize
    mapping = {
        "CST and Department": "CST",
        "CST / CST":          "CST",
        "CST / CST / CST":    "CST",
        "ET / ET":            "ET",
        "ET / ET / ET":       "ET",
        "ET Department":      "ET",
        "ENT / ENT":          "ENT",
        "ENT / ENT / ENT":    "ENT",
        "ENT Department":     "ENT",
        "RAC / RAC":          "RAC",
        "RAC and RAC / RAC":  "RAC",
        "RAC and RAC Department": "RAC",
        "FT / FT":            "FT",
        "FT / FT / FT":       "FT",
        "FT Department":      "FT",
        "MT / MNT":           "MT",
        "MT / MNT / MNT":     "MT",
        "MNT / MT":           "MT",
        "MNT Department":     "MT",
        "MNT":                "MT",
        "Non-Tech / Non-Tech":"Non-Tech",
        "Non-Technical":      "Non-Tech",
        "General Administration": "General",
    }
    return mapping.get(raw, None)


def build_chunk_id(filename: str, item: dict, index: int) -> str:
    """
    chunk_id তৈরি করে।
    """
    base = filename.replace(".json", "").replace(" ", "_").lower()
    if "chunk_id" in item and item["chunk_id"]:
        return f"{base}_{index}_{str(item['chunk_id'])[:150]}"
    return f"{base}__{index}"


def extract_chunk(filename: str, item: dict, index: int) -> dict | None:
    """
    একটি JSON item থেকে documents table-এর জন্য
    প্রয়োজনীয় সব fields extract করে।
    None return করলে এই chunk skip করা হবে।
    """
    cfg = FILE_CONFIG.get(filename, {})

    # ── content ──
    content = item.get("context_text", "").strip()
    if not content or len(content) < 10:
        return None   # empty content skip

    # ── chunk_id ──
    chunk_id = build_chunk_id(filename, item, index)

    # ── doc_type ──
    doc_type = (
        item.get("doc_type")
        or cfg.get("doc_type_default", "general")
    )
    doc_type = str(doc_type).strip()[:100]

    # ── topic ──
    topic = item.get("topic", "")
    if not topic:
        topic = item.get("topic", "")
    topic = str(topic).strip()[:500] if topic else None

    # ── department ──
    dept_field = cfg.get("dept_field")
    raw_dept = None
    if dept_field:
        raw_dept = item.get(dept_field)
    # lab_info_where.json-এ metadata.department আছে
    if not raw_dept and "metadata" in item and isinstance(item["metadata"], dict):
        raw_dept = item["metadata"].get("department")
    department = normalize_department(raw_dept)

    # ── meta ──
    meta = {}
    keep_fields = cfg.get("keep_as_meta", [])
    for field in keep_fields:
        val = item.get(field)
        if val is not None:
            # list বা dict JSON serializable হওয়া দরকার
            if isinstance(val, (str, int, float, bool, list, dict)):
                meta[field] = val
            else:
                meta[field] = str(val)

    # lab_info_where.json-এর nested metadata যোগ করা হবে
    if "metadata" in item and isinstance(item["metadata"], dict):
        for k, v in item["metadata"].items():
            if k not in meta:
                meta[k] = v

    return {
        "chunk_id":    chunk_id,
        "content":     content,
        "doc_type":    doc_type,
        "topic":       topic,
        "department":  department,
        "meta":        meta,
        "source_file": filename,
    }


def upsert_batch(conn, rows_with_embeddings: list[dict]):
    """
    একটি batch documents table-এ upsert করে।
    chunk_id conflict হলে সব fields update করে।
    """
    if not rows_with_embeddings:
        return 0

    records = []
    for r in rows_with_embeddings:
        vec_str = "[" + ",".join(f"{v:.8f}" for v in r["embedding"]) + "]"
        records.append((
            r["chunk_id"],
            r["content"],
            r["doc_type"],
            r["topic"],
            r["department"],
            vec_str,
            json.dumps(r["meta"], ensure_ascii=False),
            r["source_file"],
        ))

    sql = f"""
        INSERT INTO {TABLE}
            (chunk_id, content, doc_type, topic, department,
             embedding, meta, source_file)
        VALUES %s
        ON CONFLICT (chunk_id) DO UPDATE SET
            content     = EXCLUDED.content,
            doc_type    = EXCLUDED.doc_type,
            topic       = EXCLUDED.topic,
            department  = EXCLUDED.department,
            embedding   = EXCLUDED.embedding,
            meta        = EXCLUDED.meta,
            source_file = EXCLUDED.source_file,
            updated_at  = NOW();
    """

    template = "(%s, %s, %s, %s, %s, %s::vector, %s::jsonb, %s)"

    with conn.cursor() as cur:
        execute_values(cur, sql, records, template=template)
    conn.commit()
    return len(records)


def process_file(filename: str, conn) -> tuple[int, int, int]:
    """
    একটি JSON file process করে।
    Returns: (total_items, inserted, skipped)
    """
    filepath = DOCS_DIR / filename
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    chunks = []
    skipped = 0
    for i, item in enumerate(data):
        chunk = extract_chunk(filename, item, i)
        if chunk is None:
            skipped += 1
        else:
            chunks.append(chunk)

    if not chunks:
        return len(data), 0, skipped

    # Batch embed করা
    inserted = 0
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        texts = [c["content"] for c in batch]

        try:
            embeddings = embed_batch(texts)
            for chunk, emb in zip(batch, embeddings):
                chunk["embedding"] = emb
            inserted += upsert_batch(conn, batch)
        except psycopg2.errors.UniqueViolation:
            print(f"\n  [ERROR] batch {start}-{start+len(batch)}: Duplicate chunk_id in the same batch. Resolving individually...")
            conn.rollback()
            # Try inserting one by one
            for i, chunk in enumerate(batch):
                try:
                    chunk["embedding"] = embeddings[i]
                    inserted += upsert_batch(conn, [chunk])
                except Exception as inner_e:
                    print(f"    -> [SKIP] chunk {chunk['chunk_id']}: {inner_e}")
                    conn.rollback()
                    skipped += 1
        except Exception as e:
            print(f"\n  [ERROR] batch {start}-{start+len(batch)}: {e}")
            conn.rollback()
            skipped += len(batch)

    return len(data), inserted, skipped


# ─── Main ─────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CNPI RAG — Document Seed Script")
    print("=" * 60)
    print(f"  Source : {DOCS_DIR}")
    print(f"  Table  : {TABLE}")
    print(f"  Batch  : {BATCH_SIZE} chunks per embed call")
    print()

    # DB connect
    print("[1/3] Connecting to database...")
    try:
        conn = get_db_connection()
        conn.autocommit = False
        print("  [OK] Connected")
    except Exception as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # embedding model load
    print()
    print("[2/3] Loading embedding model...")
    try:
        get_embedding_model()
        print("  [OK] Model ready")
    except Exception as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # Process each file
    print()
    print("[3/3] Processing JSON files...")
    print()

    json_files = sorted(DOCS_DIR.glob("*.json"))
    total_inserted = 0
    total_skipped  = 0
    t_start = time.time()

    for filepath in json_files:
        filename = filepath.name
        print(f"  ▸ {filename:<45}", end="", flush=True)
        t0 = time.time()

        try:
            total, inserted, skipped = process_file(filename, conn)
            elapsed = time.time() - t0
            print(f"  {inserted:>3} inserted  {skipped:>2} skipped  ({elapsed:.1f}s)")
            total_inserted += inserted
            total_skipped  += skipped
        except Exception as e:
            print(f"  [ERROR] {e}")
            conn.rollback()

    conn.close()
    elapsed_total = time.time() - t_start

    print()
    print("=" * 60)
    print(f"  Total inserted : {total_inserted}")
    print(f"  Total skipped  : {total_skipped}")
    print(f"  Time elapsed   : {elapsed_total:.1f}s")
    print()

    # Final verify
    print("  Verifying database...")
    verify_conn = get_db_connection()
    cur = verify_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM public.documents")
    count = cur.fetchone()[0]
    cur.execute("SELECT doc_type, COUNT(*) FROM public.documents GROUP BY doc_type ORDER BY COUNT(*) DESC")
    breakdown = cur.fetchall()
    verify_conn.close()

    print(f"  Total rows in documents: {count}")
    print()
    print("  Breakdown by doc_type:")
    for doc_type, cnt in breakdown:
        print(f"    {doc_type:<40} {cnt:>4}")
    print()
    print("  [DONE] Seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
