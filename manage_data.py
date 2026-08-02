"""
==========================================================
CNPI RAG - Data Management Script
==========================================================
Interactive script to manage the `documents` table data:
  - View all documents / by doc_type / by department
  - Add a new document (with auto embedding)
  - Update an existing document (content, topic, department)
  - Delete a document by chunk_id
  - Search documents
  - View statistics

Usage:
    cd G:\\CNPI_Hybrid_RAG
    python manage_data.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Make sure Cnpi_RAG is on the path so we can import embedding_utils
_project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_project_root / "Cnpi_RAG"))

TABLE = "public.documents"
VALID_DEPTS = ["CST", "ET", "ENT", "RAC", "FT", "MT", "Non-Tech", "General"]


# =============================================================================
# Database connection
# =============================================================================

def get_conn():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "college"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
    )
    return conn


def run_query(sql, params=None, fetch=False):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            if fetch:
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            else:
                conn.commit()
                return cur.rowcount
    except Exception as e:
        conn.rollback()
        print(f"  [ERROR] {e}")
        return [] if fetch else 0
    finally:
        conn.close()


# =============================================================================
# Embedding
# =============================================================================

def get_embedding(text):
    """Generate embedding vector for the given text."""
    from utils.embedding_utils import embed_text
    return embed_text(text)


def vec_to_pg_literal(vec):
    """Convert float list to PostgreSQL vector literal."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


# =============================================================================
# View functions
# =============================================================================

def view_all(limit=50):
    """View all documents (limited)."""
    rows = run_query(f"""
        SELECT doc_id, chunk_id, doc_type, department, topic,
               LEFT(content, 80) AS content_preview, updated_at
        FROM {TABLE}
        ORDER BY doc_id
        LIMIT %s
    """, (limit,), fetch=True)

    if not rows:
        print("  No documents found.")
        return

    print(f"\n  {'ID':<5} {'chunk_id':<45} {'doc_type':<30} {'dept':<10} {'topic':<30}")
    print("  " + "-" * 130)
    for r in rows:
        print(f"  {r['doc_id']:<5} {str(r['chunk_id'])[:43]:<45} {str(r['doc_type'])[:28]:<30} "
              f"{str(r['department'] or '-'):<10} {str(r['topic'] or '-')[:28]:<30}")
    print(f"\n  Showing {len(rows)} documents (limit={limit}).")


def view_by_doc_type():
    """View documents filtered by doc_type."""
    types = run_query(f"SELECT DISTINCT doc_type FROM {TABLE} ORDER BY doc_type", fetch=True)
    if not types:
        print("  No documents found.")
        return

    print("\n  Available doc_types:")
    for i, t in enumerate(types, 1):
        print(f"    {i}. {t['doc_type']}")

    choice = input("\n  Select doc_type number: ").strip()
    try:
        doc_type = types[int(choice) - 1]["doc_type"]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    rows = run_query(f"""
        SELECT doc_id, chunk_id, department, topic, LEFT(content, 80) AS content_preview
        FROM {TABLE}
        WHERE doc_type = %s
        ORDER BY doc_id
    """, (doc_type,), fetch=True)

    if not rows:
        print(f"  No documents with doc_type='{doc_type}'.")
        return

    print(f"\n  Documents with doc_type='{doc_type}' ({len(rows)} rows):")
    print(f"  {'ID':<5} {'chunk_id':<45} {'dept':<10} {'topic':<30} {'content':<80}")
    print("  " + "-" * 175)
    for r in rows:
        print(f"  {r['doc_id']:<5} {str(r['chunk_id'])[:43]:<45} {str(r['department'] or '-'):<10} "
              f"{str(r['topic'] or '-')[:28]:<30} {str(r['content_preview'] or '-')[:78]:<80}")


def view_by_department():
    """View documents filtered by department."""
    print(f"\n  Valid departments: {', '.join(VALID_DEPTS)}")
    dept = input("  Enter department (or press Enter to see all): ").strip()

    if dept and dept not in VALID_DEPTS:
        print(f"  Invalid department. Valid: {', '.join(VALID_DEPTS)}")
        return

    if dept:
        rows = run_query(f"""
            SELECT doc_id, chunk_id, doc_type, topic, LEFT(content, 80) AS content_preview
            FROM {TABLE}
            WHERE department = %s
            ORDER BY doc_id
        """, (dept,), fetch=True)
    else:
        rows = run_query(f"""
            SELECT doc_id, chunk_id, doc_type, department, topic,
                   LEFT(content, 80) AS content_preview
            FROM {TABLE}
            ORDER BY doc_id
        """, fetch=True)

    if not rows:
        print(f"  No documents found for department='{dept or 'ALL'}'.")
        return

    print(f"\n  Documents for department='{dept or 'ALL'}' ({len(rows)} rows):")
    print(f"  {'ID':<5} {'chunk_id':<45} {'doc_type':<30} {'dept':<10} {'content':<80}")
    print("  " + "-" * 175)
    for r in rows:
        print(f"  {r['doc_id']:<5} {str(r['chunk_id'])[:43]:<45} {str(r['doc_type'])[:28]:<30} "
              f"{str(r.get('department') or '-'):<10} {str(r['content_preview'] or '-')[:78]:<80}")


def view_statistics():
    """View database statistics."""
    total = run_query(f"SELECT COUNT(*) AS cnt FROM {TABLE}", fetch=True)
    total_count = total[0]["cnt"] if total else 0

    by_type = run_query(f"""
        SELECT doc_type, COUNT(*) AS cnt
        FROM {TABLE}
        GROUP BY doc_type
        ORDER BY cnt DESC
    """, fetch=True)

    by_dept = run_query(f"""
        SELECT COALESCE(department, '(NULL)') AS dept, COUNT(*) AS cnt
        FROM {TABLE}
        GROUP BY department
        ORDER BY cnt DESC
    """, fetch=True)

    print(f"\n  === Documents Table Statistics ===")
    print(f"  Total documents: {total_count}")
    print(f"\n  By doc_type:")
    for r in by_type:
        print(f"    {r['doc_type']:<40} {r['cnt']:>4}")
    print(f"\n  By department:")
    for r in by_dept:
        print(f"    {r['dept']:<15} {r['cnt']:>4}")


def view_single():
    """View a single document in full by chunk_id or doc_id."""
    key = input("  Enter chunk_id or doc_id: ").strip()
    if not key:
        return

    if key.isdigit():
        rows = run_query(f"""
            SELECT doc_id, chunk_id, content, doc_type, topic, department,
                   meta, source_file, created_at, updated_at
            FROM {TABLE}
            WHERE doc_id = %s
        """, (int(key),), fetch=True)
    else:
        rows = run_query(f"""
            SELECT doc_id, chunk_id, content, doc_type, topic, department,
                   meta, source_file, created_at, updated_at
            FROM {TABLE}
            WHERE chunk_id = %s
        """, (key,), fetch=True)

    if not rows:
        print("  Document not found.")
        return

    r = rows[0]
    print(f"\n  === Document Details ===")
    print(f"  doc_id      : {r['doc_id']}")
    print(f"  chunk_id    : {r['chunk_id']}")
    print(f"  doc_type    : {r['doc_type']}")
    print(f"  topic       : {r['topic']}")
    print(f"  department  : {r['department']}")
    print(f"  source_file : {r['source_file']}")
    print(f"  created_at  : {r['created_at']}")
    print(f"  updated_at  : {r['updated_at']}")
    print(f"\n  Content:")
    print(f"  {r['content']}")
    print(f"\n  Meta:")
    print(f"  {json.dumps(r['meta'], ensure_ascii=False, indent=2)}")


# =============================================================================
# Add / Update / Delete
# =============================================================================

def add_document():
    """Add a new document to the documents table."""
    print("\n  === Add New Document ===")

    chunk_id = input("  chunk_id (unique ID, e.g. 'manual_cst_ci_1'): ").strip()
    if not chunk_id:
        print("  chunk_id is required.")
        return

    # Check if chunk_id already exists
    existing = run_query(f"SELECT doc_id FROM {TABLE} WHERE chunk_id = %s", (chunk_id,), fetch=True)
    if existing:
        print(f"  [ERROR] chunk_id '{chunk_id}' already exists (doc_id={existing[0]['doc_id']}).")
        print("  Use 'Update' option instead.")
        return

    content = input("  content (the main text, min 10 chars): ").strip()
    if len(content) < 10:
        print("  Content must be at least 10 characters.")
        return

    doc_type = input("  doc_type (e.g. teachers_info, class_routine) [default: general]: ").strip()
    if not doc_type:
        doc_type = "general"

    topic = input("  topic (optional, e.g. 'CST 5th Semester CI'): ").strip() or None

    print(f"  Valid departments: {', '.join(VALID_DEPTS)}")
    dept_input = input("  department (optional, press Enter for NULL): ").strip()
    department = dept_input if dept_input in VALID_DEPTS else None

    meta_input = input("  meta (JSON, e.g. {\"name\": \"Rahim\", \"phone\": \"017xx\"}) [default: {{}}]: ").strip()
    if meta_input:
        try:
            meta = json.loads(meta_input)
        except json.JSONDecodeError:
            print("  Invalid JSON. Using empty meta.")
            meta = {}
    else:
        meta = {}

    source_file = input("  source_file (optional, e.g. 'manual_entry'): ").strip() or None

    # Generate embedding
    print("  Generating embedding...")
    try:
        embedding = get_embedding(content)
        vec_str = vec_to_pg_literal(embedding)
    except Exception as e:
        print(f"  [ERROR] Embedding failed: {e}")
        return

    # Insert
    result = run_query(f"""
        INSERT INTO {TABLE}
            (chunk_id, content, doc_type, topic, department, embedding, meta, source_file)
        VALUES
            (%s, %s, %s, %s, %s, %s::vector, %s::jsonb, %s)
        ON CONFLICT (chunk_id) DO UPDATE SET
            content = EXCLUDED.content,
            doc_type = EXCLUDED.doc_type,
            topic = EXCLUDED.topic,
            department = EXCLUDED.department,
            embedding = EXCLUDED.embedding,
            meta = EXCLUDED.meta,
            source_file = EXCLUDED.source_file,
            updated_at = NOW()
    """, (chunk_id, content, doc_type, topic, department, vec_str,
          json.dumps(meta, ensure_ascii=False), source_file), fetch=False)

    if result:
        print(f"  [OK] Document '{chunk_id}' added successfully!")
    else:
        print(f"  [ERROR] Failed to add document.")


def update_document():
    """Update an existing document."""
    print("\n  === Update Document ===")

    chunk_id = input("  Enter chunk_id to update: ").strip()
    if not chunk_id:
        return

    existing = run_query(f"""
        SELECT doc_id, chunk_id, content, doc_type, topic, department, meta
        FROM {TABLE}
        WHERE chunk_id = %s
    """, (chunk_id,), fetch=True)

    if not existing:
        print(f"  Document '{chunk_id}' not found.")
        return

    r = existing[0]
    print(f"\n  Current values:")
    print(f"    doc_type   : {r['doc_type']}")
    print(f"    topic      : {r['topic']}")
    print(f"    department : {r['department']}")
    print(f"    content    : {str(r['content'])[:100]}...")

    print(f"\n  Enter new values (press Enter to keep current):")

    new_content = input(f"  content: ").strip()
    if not new_content:
        new_content = r["content"]

    new_doc_type = input(f"  doc_type [{r['doc_type']}]: ").strip() or r["doc_type"]

    new_topic = input(f"  topic [{r['topic']}]: ").strip()
    new_topic = new_topic if new_topic else r["topic"]

    print(f"  Valid departments: {', '.join(VALID_DEPTS)}")
    dept_input = input(f"  department [{r['department']}]: ").strip()
    if dept_input == "":
        new_dept = r["department"]
    elif dept_input in VALID_DEPTS:
        new_dept = dept_input
    else:
        print(f"  Invalid department. Keeping current: {r['department']}")
        new_dept = r["department"]

    # Regenerate embedding only if content changed
    if new_content != r["content"]:
        print("  Content changed — regenerating embedding...")
        try:
            embedding = get_embedding(new_content)
            vec_str = vec_to_pg_literal(embedding)
        except Exception as e:
            print(f"  [ERROR] Embedding failed: {e}")
            return
    else:
        vec_str = None

    if vec_str:
        result = run_query(f"""
            UPDATE {TABLE} SET
                content = %s,
                doc_type = %s,
                topic = %s,
                department = %s,
                embedding = %s::vector,
                updated_at = NOW()
            WHERE chunk_id = %s
        """, (new_content, new_doc_type, new_topic, new_dept, vec_str, chunk_id), fetch=False)
    else:
        result = run_query(f"""
            UPDATE {TABLE} SET
                content = %s,
                doc_type = %s,
                topic = %s,
                department = %s,
                updated_at = NOW()
            WHERE chunk_id = %s
        """, (new_content, new_doc_type, new_topic, new_dept, chunk_id), fetch=False)

    if result:
        print(f"  [OK] Document '{chunk_id}' updated successfully!")
    else:
        print(f"  [ERROR] Failed to update document.")


def delete_document():
    """Delete a document by chunk_id."""
    print("\n  === Delete Document ===")

    chunk_id = input("  Enter chunk_id to delete: ").strip()
    if not chunk_id:
        return

    existing = run_query(f"""
        SELECT doc_id, chunk_id, doc_type, LEFT(content, 60) AS preview
        FROM {TABLE}
        WHERE chunk_id = %s
    """, (chunk_id,), fetch=True)

    if not existing:
        print(f"  Document '{chunk_id}' not found.")
        return

    r = existing[0]
    print(f"\n  Found document:")
    print(f"    doc_id  : {r['doc_id']}")
    print(f"    chunk_id: {r['chunk_id']}")
    print(f"    doc_type: {r['doc_type']}")
    print(f"    content : {r['preview']}...")

    confirm = input(f"\n  Are you sure you want to DELETE this? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Deletion cancelled.")
        return

    result = run_query(f"DELETE FROM {TABLE} WHERE chunk_id = %s", (chunk_id,), fetch=False)
    if result:
        print(f"  [OK] Document '{chunk_id}' deleted successfully!")
    else:
        print(f"  [ERROR] Failed to delete document.")


def search_documents():
    """Search documents by keyword in content."""
    keyword = input("  Enter search keyword: ").strip()
    if not keyword:
        return

    rows = run_query(f"""
        SELECT doc_id, chunk_id, doc_type, department, topic,
               LEFT(content, 100) AS content_preview
        FROM {TABLE}
        WHERE content ILIKE %s
        ORDER BY doc_id
        LIMIT 30
    """, (f"%{keyword}%",), fetch=True)

    if not rows:
        print(f"  No documents matching '{keyword}'.")
        return

    print(f"\n  Search results for '{keyword}' ({len(rows)} rows):")
    print(f"  {'ID':<5} {'chunk_id':<45} {'doc_type':<30} {'content':<100}")
    print("  " + "-" * 185)
    for r in rows:
        print(f"  {r['doc_id']:<5} {str(r['chunk_id'])[:43]:<45} {str(r['doc_type'])[:28]:<30} "
              f"{str(r['content_preview'] or '-')[:98]:<100}")


# =============================================================================
# Main menu
# =============================================================================

MENU = """
==========================================================
  CNPI RAG - Data Management (documents table)
==========================================================

  1. View all documents (first 50)
  2. View by doc_type
  3. View by department
  4. View single document (full details)
  5. View statistics
  6. Search documents (keyword)
  7. Add new document
  8. Update existing document
  9. Delete document
  10. Manage SQL tables (people, departments, designations)
  0. Exit

----------------------------------------------------------
"""


def main():
    while True:
        print(MENU)
        choice = input("  Select option: ").strip()

        if choice == "1":
            view_all()
        elif choice == "2":
            view_by_doc_type()
        elif choice == "3":
            view_by_department()
        elif choice == "4":
            view_single()
        elif choice == "5":
            view_statistics()
        elif choice == "6":
            search_documents()
        elif choice == "7":
            add_document()
        elif choice == "8":
            update_document()
        elif choice == "9":
            delete_document()
        elif choice == "10":
            manage_sql_tables()
        elif choice == "0":
            print("\n  Goodbye!")
            break
        else:
            print("  Invalid option.")

        input("\n  Press Enter to continue...")


# =============================================================================
# SQL Tables management (people, departments, designations)
# =============================================================================

SQL_MENU = """
  ----------------------------------------------------------
  SQL Tables Management (people, departments, designations)
  ----------------------------------------------------------

    1. View all departments
    2. Add a department
    3. View all designations
    4. Add a designation
    5. View all people (teachers/staff)
    6. View people by department
    7. Add a person (teacher/staff)
    8. Update a person
    9. Delete a person
    0. Back to main menu

  ----------------------------------------------------------
"""

DESIGNATION_CATEGORIES = [
    "Academic Leadership", "Teacher", "Craft Instructor",
    "Lab Staff", "Administrative", "Library", "Support Staff"
]
EMPLOYMENT_TYPES = ["Permanent", "Part-Time", "Contractual", "Outsourced"]
SHIFTS = ["1st", "2nd", "Both"]


def manage_sql_tables():
    while True:
        print(SQL_MENU)
        choice = input("  Select option: ").strip()

        if choice == "1":
            view_departments()
        elif choice == "2":
            add_department()
        elif choice == "3":
            view_designations()
        elif choice == "4":
            add_designation()
        elif choice == "5":
            view_people()
        elif choice == "6":
            view_people_by_dept()
        elif choice == "7":
            add_person()
        elif choice == "8":
            update_person()
        elif choice == "9":
            delete_person()
        elif choice == "0":
            break
        else:
            print("  Invalid option.")

        input("\n  Press Enter to continue...")


def get_institution_id():
    """Get the institution_id for CNPI."""
    rows = run_query("SELECT institution_id, short_name FROM institutions LIMIT 1", fetch=True)
    if rows:
        return rows[0]["institution_id"]
    return 1


def view_departments():
    rows = run_query("""
        SELECT d.department_id, d.name_en, d.name_bn, d.short_code,
               d.shift_info, d.total_teachers, d.total_labs
        FROM departments d
        ORDER BY d.department_id
    """, fetch=True)

    if not rows:
        print("  No departments found.")
        return

    print(f"\n  {'ID':<5} {'name_en':<35} {'short_code':<12} {'shift_info':<20} {'teachers':<10} {'labs':<5}")
    print("  " + "-" * 90)
    for r in rows:
        print(f"  {r['department_id']:<5} {str(r['name_en'])[:33]:<35} "
              f"{str(r['short_code']):<12} {str(r['shift_info'] or '-'):<20} "
              f"{str(r['total_teachers'] or '-'):<10} {str(r['total_labs'] or '-'):<5}")


def add_department():
    print("\n  === Add Department ===")
    name_en = input("  name_en (e.g. Computer Science and Technology): ").strip()
    if not name_en:
        print("  name_en is required.")
        return

    name_bn = input("  name_bn (Bengali name, optional): ").strip() or None
    short_code = input("  short_code (e.g. CST, ET, ENT, RAC, FT, MT): ").strip().upper()
    if not short_code:
        print("  short_code is required.")
        return

    shift_info = input("  shift_info (e.g. 'Both Shifts', '1st Shift (Morning)') [default: Both Shifts]: ").strip()
    if not shift_info:
        shift_info = "Both Shifts"

    total_teachers = input("  total_teachers (optional number): ").strip()
    total_teachers = int(total_teachers) if total_teachers.isdigit() else None

    total_labs = input("  total_labs (optional number): ").strip()
    total_labs = int(total_labs) if total_labs.isdigit() else None

    inst_id = get_institution_id()

    result = run_query("""
        INSERT INTO departments (institution_id, name_en, name_bn, short_code, shift_info, total_teachers, total_labs)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (short_code) DO UPDATE SET
            name_en = EXCLUDED.name_en,
            name_bn = EXCLUDED.name_bn,
            shift_info = EXCLUDED.shift_info,
            total_teachers = EXCLUDED.total_teachers,
            total_labs = EXCLUDED.total_labs
    """, (inst_id, name_en, name_bn, short_code, shift_info, total_teachers, total_labs), fetch=False)

    if result:
        print(f"  [OK] Department '{short_code}' added/updated!")
    else:
        print(f"  [ERROR] Failed to add department.")


def view_designations():
    rows = run_query("""
        SELECT designation_id, title_bn, title_en, category, rank_level
        FROM designations
        ORDER BY rank_level, designation_id
    """, fetch=True)

    if not rows:
        print("  No designations found.")
        return

    print(f"\n  {'ID':<5} {'title_bn':<35} {'title_en':<35} {'category':<25} {'rank':<5}")
    print("  " + "-" * 105)
    for r in rows:
        print(f"  {r['designation_id']:<5} {str(r['title_bn'])[:33]:<35} "
              f"{str(r['title_en'] or '-')[:33]:<35} {str(r['category']):<25} "
              f"{str(r['rank_level'] or '-'):<5}")


def add_designation():
    print("\n  === Add Designation ===")
    title_bn = input("  title_bn (Bengali title, e.g. প্রধান শিক্ষক): ").strip()
    if not title_bn:
        print("  title_bn is required.")
        return

    title_en = input("  title_en (English title, optional): ").strip() or None

    print(f"  Valid categories: {', '.join(DESIGNATION_CATEGORIES)}")
    category = input("  category: ").strip()
    if category not in DESIGNATION_CATEGORIES:
        print(f"  Invalid category. Valid: {', '.join(DESIGNATION_CATEGORIES)}")
        return

    rank_input = input("  rank_level (1=Principal, 2=Vice Principal, 3=CI, 4=Instructor, 5=Junior): ").strip()
    rank_level = int(rank_input) if rank_input.isdigit() else None

    result = run_query("""
        INSERT INTO designations (title_bn, title_en, category, rank_level)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (title_bn) DO UPDATE SET
            title_en = EXCLUDED.title_en,
            category = EXCLUDED.category,
            rank_level = EXCLUDED.rank_level
    """, (title_bn, title_en, category, rank_level), fetch=False)

    if result:
        print(f"  [OK] Designation '{title_bn}' added/updated!")
    else:
        print(f"  [ERROR] Failed to add designation.")


def view_people(limit=50):
    rows = run_query("""
        SELECT p.person_id, p.name_bn, p.name_en, p.gender,
               d.short_code AS department, des.title_bn AS designation,
               p.employment_type, p.shift, p.is_chief_instructor,
               p.phone_primary, p.email
        FROM people p
        LEFT JOIN departments d ON p.department_id = d.department_id
        LEFT JOIN designations des ON p.designation_id = des.designation_id
        ORDER BY p.person_id
        LIMIT %s
    """, (limit,), fetch=True)

    if not rows:
        print("  No people found.")
        return

    print(f"\n  {'ID':<5} {'name_bn':<25} {'dept':<8} {'designation':<25} {'type':<12} {'shift':<7} {'CI':<4} {'phone':<15}")
    print("  " + "-" * 105)
    for r in rows:
        ci = "YES" if r["is_chief_instructor"] else "-"
        print(f"  {r['person_id']:<5} {str(r['name_bn'])[:23]:<25} "
              f"{str(r['department'] or '-'):<8} {str(r['designation'] or '-')[:23]:<25} "
              f"{str(r['employment_type']):<12} {str(r['shift'] or '-'):<7} {ci:<4} "
              f"{str(r['phone_primary'] or '-'):<15}")
    print(f"\n  Showing {len(rows)} people (limit={limit}).")


def view_people_by_dept():
    view_departments()
    dept_input = input("\n  Enter department short_code (e.g. CST): ").strip().upper()
    if not dept_input:
        return

    rows = run_query("""
        SELECT p.person_id, p.name_bn, p.name_en, p.gender,
               d.short_code AS department, des.title_bn AS designation,
               p.employment_type, p.shift, p.is_chief_instructor,
               p.phone_primary, p.phone_secondary, p.email
        FROM people p
        LEFT JOIN departments d ON p.department_id = d.department_id
        LEFT JOIN designations des ON p.designation_id = des.designation_id
        WHERE d.short_code = %s
        ORDER BY p.person_id
    """, (dept_input,), fetch=True)

    if not rows:
        print(f"  No people found in department '{dept_input}'.")
        return

    print(f"\n  People in department '{dept_input}' ({len(rows)} rows):")
    print(f"  {'ID':<5} {'name_bn':<25} {'designation':<25} {'type':<12} {'shift':<7} {'CI':<4} {'phone':<15} {'email':<20}")
    print("  " + "-" * 120)
    for r in rows:
        ci = "YES" if r["is_chief_instructor"] else "-"
        print(f"  {r['person_id']:<5} {str(r['name_bn'])[:23]:<25} "
              f"{str(r['designation'] or '-')[:23]:<25} {str(r['employment_type']):<12} "
              f"{str(r['shift'] or '-'):<7} {ci:<4} {str(r['phone_primary'] or '-'):<15} "
              f"{str(r['email'] or '-')[:18]:<20}")


def add_person():
    print("\n  === Add Person (Teacher/Staff) ===")

    name_bn = input("  name_bn (Bengali name, required): ").strip()
    if not name_bn:
        print("  name_bn is required.")
        return

    name_en = input("  name_en (English name, optional): ").strip() or None

    gender = input("  gender (M/F, optional): ").strip().upper()
    if gender not in ("M", "F"):
        gender = None

    # Department selection
    print("\n  Available departments:")
    depts = run_query("SELECT department_id, short_code, name_en FROM departments ORDER BY department_id", fetch=True)
    if depts:
        for i, d in enumerate(depts, 1):
            print(f"    {i}. {d['short_code']} - {d['name_en']}")
    dept_choice = input("  Select department number (or press Enter for NULL): ").strip()
    department_id = None
    if dept_choice.isdigit() and depts:
        try:
            department_id = depts[int(dept_choice) - 1]["department_id"]
        except (ValueError, IndexError):
            pass

    # Designation selection
    print("\n  Available designations:")
    desigs = run_query("SELECT designation_id, title_bn, category FROM designations ORDER BY rank_level, designation_id", fetch=True)
    if desigs:
        for i, d in enumerate(desigs, 1):
            print(f"    {i}. {d['title_bn']} ({d['category']})")
    desig_choice = input("  Select designation number (or press Enter for NULL): ").strip()
    designation_id = None
    if desig_choice.isdigit() and desigs:
        try:
            designation_id = desigs[int(desig_choice) - 1]["designation_id"]
        except (ValueError, IndexError):
            pass

    print(f"\n  Employment types: {', '.join(EMPLOYMENT_TYPES)}")
    employment_type = input("  employment_type [default: Permanent]: ").strip()
    if employment_type not in EMPLOYMENT_TYPES:
        employment_type = "Permanent"

    print(f"  Shifts: {', '.join(SHIFTS)}")
    shift = input("  shift (optional): ").strip()
    if shift not in SHIFTS:
        shift = None

    phone_primary = input("  phone_primary (optional): ").strip() or None
    phone_secondary = input("  phone_secondary (optional): ").strip() or None
    email = input("  email (optional): ").strip() or None

    is_ci = input("  is_chief_instructor? (yes/no) [default: no]: ").strip().lower() == "yes"
    is_principal = input("  is_principal? (yes/no) [default: no]: ").strip().lower() == "yes"
    is_vice = input("  is_vice_principal? (yes/no) [default: no]: ").strip().lower() == "yes"

    inst_id = get_institution_id()

    result = run_query("""
        INSERT INTO people (institution_id, name_bn, name_en, gender, department_id,
                           designation_id, employment_type, shift, is_principal,
                           is_vice_principal, is_chief_instructor, phone_primary,
                           phone_secondary, email)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (inst_id, name_bn, name_en, gender, department_id, designation_id,
          employment_type, shift, is_principal, is_vice, is_ci,
          phone_primary, phone_secondary, email), fetch=False)

    if result:
        print(f"\n  [OK] Person '{name_bn}' added successfully!")
    else:
        print(f"\n  [ERROR] Failed to add person.")


def update_person():
    print("\n  === Update Person ===")
    person_id = input("  Enter person_id: ").strip()
    if not person_id or not person_id.isdigit():
        print("  Invalid person_id.")
        return

    existing = run_query("""
        SELECT p.person_id, p.name_bn, p.name_en, p.gender, p.department_id,
               p.designation_id, p.employment_type, p.shift, p.is_chief_instructor,
               p.phone_primary, p.phone_secondary, p.email,
               d.short_code AS dept_code, des.title_bn AS desig_title
        FROM people p
        LEFT JOIN departments d ON p.department_id = d.department_id
        LEFT JOIN designations des ON p.designation_id = des.designation_id
        WHERE p.person_id = %s
    """, (int(person_id),), fetch=True)

    if not existing:
        print(f"  Person with id={person_id} not found.")
        return

    r = existing[0]
    print(f"\n  Current values:")
    print(f"    name_bn       : {r['name_bn']}")
    print(f"    name_en       : {r['name_en']}")
    print(f"    department    : {r['dept_code']}")
    print(f"    designation   : {r['desig_title']}")
    print(f"    employment    : {r['employment_type']}")
    print(f"    shift         : {r['shift']}")
    print(f"    is_ci         : {r['is_chief_instructor']}")
    print(f"    phone_primary : {r['phone_primary']}")

    print(f"\n  Enter new values (press Enter to keep current):")

    new_name_bn = input(f"  name_bn: ").strip() or r["name_bn"]
    new_name_en = input(f"  name_en [{r['name_en']}]: ").strip() or r["name_en"]

    new_phone = input(f"  phone_primary [{r['phone_primary']}]: ").strip()
    new_phone = new_phone if new_phone else r["phone_primary"]

    new_phone2 = input(f"  phone_secondary [{r['phone_secondary']}]: ").strip()
    new_phone2 = new_phone2 if new_phone2 else r["phone_secondary"]

    new_email = input(f"  email [{r['email']}]: ").strip()
    new_email = new_email if new_email else r["email"]

    print(f"  Shifts: {', '.join(SHIFTS)}")
    new_shift = input(f"  shift [{r['shift']}]: ").strip()
    if new_shift not in SHIFTS:
        new_shift = r["shift"]

    is_ci = input(f"  is_chief_instructor? (yes/no) [{'yes' if r['is_chief_instructor'] else 'no'}]: ").strip().lower()
    if is_ci == "yes":
        new_ci = True
    elif is_ci == "no":
        new_ci = False
    else:
        new_ci = r["is_chief_instructor"]

    result = run_query("""
        UPDATE people SET
            name_bn = %s,
            name_en = %s,
            shift = %s,
            is_chief_instructor = %s,
            phone_primary = %s,
            phone_secondary = %s,
            email = %s
        WHERE person_id = %s
    """, (new_name_bn, new_name_en, new_shift, new_ci,
          new_phone, new_phone2, new_email, int(person_id)), fetch=False)

    if result:
        print(f"\n  [OK] Person id={person_id} updated!")
    else:
        print(f"\n  [ERROR] Failed to update person.")


def delete_person():
    print("\n  === Delete Person ===")
    person_id = input("  Enter person_id: ").strip()
    if not person_id or not person_id.isdigit():
        print("  Invalid person_id.")
        return

    existing = run_query("""
        SELECT p.person_id, p.name_bn, d.short_code AS dept
        FROM people p
        LEFT JOIN departments d ON p.department_id = d.department_id
        WHERE p.person_id = %s
    """, (int(person_id),), fetch=True)

    if not existing:
        print(f"  Person with id={person_id} not found.")
        return

    r = existing[0]
    print(f"\n  Found: id={r['person_id']}, name={r['name_bn']}, dept={r['dept']}")

    confirm = input(f"  Are you sure you want to DELETE this person? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Deletion cancelled.")
        return

    result = run_query("DELETE FROM people WHERE person_id = %s", (int(person_id),), fetch=False)
    if result:
        print(f"  [OK] Person id={person_id} deleted!")
    else:
        print(f"  [ERROR] Failed to delete person.")


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    print("\n  Testing database connection...")
    try:
        conn = get_conn()
        print("  [OK] Database connection successful!")
        conn.close()
    except Exception as e:
        print(f"  [ERROR] Database connection failed: {e}")
        print("  Check your .env file (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT).")
        sys.exit(1)

    main()
