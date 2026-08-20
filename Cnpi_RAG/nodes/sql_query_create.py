"""
SQL Query Create Node - Phase 2
================================

This node generates SQL queries for the notices table to retrieve
latest/last N notices based on created_at timestamp.

Flow: normalized_query → SQL query generation → query_str
"""

import sys
from pathlib import Path
from datetime import datetime
import re

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm, extract_content
from utils.db_utils import execute_query
from langchain_core.prompts import ChatPromptTemplate


# SQL Query Generation Prompt for All Tables
_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an SQL Query Generation Expert for the CNPI College Database.

Generate PostgreSQL queries for the following tables based on user queries.

==================================================
NOTICES TABLE — DATABASE SCHEMA (PRIMARY)
==================================================

CREATE TABLE notices(
    notice_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL,
    category VARCHAR(60),
    title_bn TEXT NOT NULL,
    content_bn TEXT NOT NULL,
    faq_bn TEXT,
    temporal_analysis JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CRITICAL COLUMNS FOR NOTICES:
- notice_id: Unique identifier
- institution_id: Institution ID (CNPI = 1)
- category: Notice category (e.g., 'Attendance', 'Exam', 'Academic', 'Admission')
- title_bn: Notice title in Bengali (REQUIRED)
- content_bn: Notice content in Bengali (REQUIRED - MAIN FIELD)
- faq_bn: Optional FAQ content in Bengali
- temporal_analysis: JSONB with temporal metadata (notice_date, expiration_date, etc.)
- created_at: Notice creation timestamp (USE THIS FOR ORDERING)

NOTICES FILTERING (MANDATORY):
WHERE institution_id = 1
  AND (temporal_analysis->>'expiration_date' IS NULL 
       OR (temporal_analysis->>'expiration_date')::date >= CURRENT_DATE)

NOTICES ORDERING (MANDATORY):
ORDER BY created_at DESC

NOTICES COLUMNS TO SELECT:
SELECT notice_id, title_bn, content_bn, category, created_at
FROM notices
WHERE institution_id = 1 
  AND (temporal_analysis->>'expiration_date' IS NULL 
       OR (temporal_analysis->>'expiration_date')::date >= CURRENT_DATE)
ORDER BY created_at DESC
LIMIT N;

==================================================
CLASS_CAPTAINS TABLE — DATABASE SCHEMA
==================================================

CREATE TABLE class_captains(
    captain_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL DEFAULT 1,
    department VARCHAR(20) NOT NULL,
    shift VARCHAR(20) NOT NULL,
    semester INTEGER NOT NULL,
    captain_name VARCHAR(100) NOT NULL,
    student_id VARCHAR(30),
    phone VARCHAR(20),
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    session_year VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    captain_rank INTEGER NOT NULL DEFAULT 1
);

IMPORTANT COLUMNS:

- captain_id → Unique captain record ID
- institution_id → Institution ID (CNPI = 1)
- department → Department name/code
- shift → Shift (1st/2nd or Morning/Day depending on stored data)
- semester → Semester number (1–8)
- captain_name → Captain's name
- student_id → Captain's student/roll ID
- phone → Captain's phone number
- email → Captain's email
- is_active → Whether the captain is currently active
- session_year → Academic session
- captain_rank → Captain position:
    1 = Main Captain
    2 = Assistant/Vice Captain

==================================================
CRITICAL CAPTAIN FILTERING
==================================================

For all captain queries:

ALWAYS include:

WHERE institution_id = 1
  AND is_active = true

This ensures that only active CNPI captains are returned.

==================================================
CAPTAIN QUERY TYPES
==================================================

1. ALL ACTIVE CAPTAINS

Use when the user asks:

- "captain gula ke?"
- "সব ক্যাপ্টেন দেখাও"
- "বর্তমান ক্যাপ্টেন কারা?"
- "active captains"
- "all class captains"

SQL Pattern:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
ORDER BY department, shift, semester, captain_rank
LIMIT 100;


2. CAPTAIN BY DEPARTMENT

Use when the user provides a department.

Examples:

- "CST department er captain ke?"
- "কম্পিউটার ডিপার্টমেন্টের ক্যাপ্টেন কে?"
- "CST er sob captain dekhao"

SQL Pattern:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
ORDER BY semester, shift, captain_rank
LIMIT 100;


3. CAPTAIN BY SEMESTER

Use when the user provides a semester.

Examples:

- "3rd semester er captain ke?"
- "৩য় সেমিস্টারের ক্যাপ্টেন কে?"
- "semester 5 captain"

SQL Pattern:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND semester = 3
ORDER BY department, shift, captain_rank
LIMIT 100;


4. CAPTAIN BY DEPARTMENT + SEMESTER

This is one of the MOST IMPORTANT query types.

Use when both department and semester are provided.

Example:

User Query:
"CST 3rd semester er captain ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
ORDER BY shift, captain_rank
LIMIT 20;


5. CAPTAIN BY DEPARTMENT + SHIFT + SEMESTER

Use when department, shift and semester are provided.

Example:

User Query:
"CST 3rd semester 1st shift er captain ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND shift ILIKE '%1st%'
  AND semester = 3
ORDER BY captain_rank
LIMIT 10;


6. MAIN CAPTAIN ONLY

captain_rank has two possible values:

1 = Main Captain
2 = Assistant/Vice Captain

If the user specifically asks:

- "main captain"
- "প্রধান ক্যাপ্টেন"
- "মূল ক্যাপ্টেন"
- "class captain কে?"

Then use:

AND captain_rank = 1

Example:

User Query:
"CST 3rd semester er main captain ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
  AND captain_rank = 1
ORDER BY shift
LIMIT 10;


7. ASSISTANT / VICE CAPTAIN

If the user asks:

- "assistant captain"
- "vice captain"
- "সহকারী ক্যাপ্টেন"

Then use:

AND captain_rank = 2

Example:

User Query:
"CST 3rd semester er assistant captain ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
  AND captain_rank = 2
ORDER BY shift
LIMIT 10;


8. CAPTAIN CONTACT INFORMATION

If the user specifically asks for:

- phone number
- mobile number
- email
- contact
- যোগাযোগ

Then retrieve the relevant contact fields.

Example:

User Query:
"CST 3rd semester er captain er phone number dao"

SQL:

SELECT
    captain_name,
    department,
    shift,
    semester,
    student_id,
    phone
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
ORDER BY shift, captain_rank
LIMIT 10;


9. CAPTAIN BY STUDENT ID

If the user provides a student ID / roll number:

Example:

User Query:
"2023-12345 kon class er captain?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND student_id = '2023-12345'
LIMIT 1;


==================================================
IMPORTANT CAPTAIN QUERY LOGIC
==================================================

1. ALWAYS filter:

institution_id = 1

2. ALWAYS filter active captains unless the user explicitly asks for inactive/former/old captains:

is_active = true

3. If department is provided:
   Use:

department ILIKE '%department%'

4. If semester is provided:
   Use:

semester = N

5. If shift is provided:
   Use:

shift ILIKE '%shift%'

6. If the user asks for main/principal captain:
   Use:

captain_rank = 1

7. If the user asks for assistant/vice captain:
   Use:

captain_rank = 2

8. If captain rank is not specified:
   DO NOT automatically filter captain_rank = 1.

   Return both rank 1 and rank 2 when both exist.

9. For a specific class, use:

department + shift + semester

when those identifiers are available.

10. For a broad request, do not unnecessarily require department,
    shift or semester.

11. For captain queries, do NOT use temporal_analysis.
    temporal_analysis belongs ONLY to the notices table.

12. Do NOT use created_at for determining the current captain.
    Use is_active = true.

13. If multiple captains match, return all matching active records
    unless the user explicitly asks for only one.

==================================================
CAPTAIN RESULT COLUMNS
==================================================

By default select:

captain_id,
department,
shift,
semester,
captain_name,
student_id,
phone,
email,
session_year,
captain_rank

Do NOT select:

institution_id

unless specifically requested.

Do NOT select:

updated_at

unless specifically requested.

==================================================
CAPTAIN NUMBER EXTRACTION
==================================================

Bengali numbers must be converted to English numbers.

Examples:

১ → 1
২ → 2
৩ → 3
৪ → 4
৫ → 5
৬ → 6
৭ → 7
৮ → 8

Examples:

"৩য় সেমিস্টার" → semester = 3

"৫ম সেমিস্টার" → semester = 5

"semester 3" → semester = 3

"3rd semester" → semester = 3

==================================================
CAPTAIN QUERY EXAMPLES
==================================================

Example 1:

User Query:
"CST 3rd semester er captain ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
ORDER BY shift, captain_rank
LIMIT 20;


Example 2:

User Query:
"CST 3rd semester 1st shift er captain ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
  AND shift ILIKE '%1st%'
ORDER BY captain_rank
LIMIT 10;


Example 3:

User Query:
"কম্পিউটার ডিপার্টমেন্টের ৫ম সেমিস্টারের সব ক্যাপ্টেন দেখাও"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%Computer%'
  AND semester = 5
ORDER BY shift, captain_rank
LIMIT 20;


Example 4:

User Query:
"CST er sob active captain dekhao"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
ORDER BY semester, shift, captain_rank
LIMIT 100;


Example 5:

User Query:
"CST 3rd semester er main captain er phone number dao"

SQL:

SELECT
    captain_name,
    department,
    shift,
    semester,
    student_id,
    phone
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND department ILIKE '%CST%'
  AND semester = 3
  AND captain_rank = 1
ORDER BY shift
LIMIT 10;


Example 6:

User Query:
"3rd semester er captain gula ke?"

SQL:

SELECT
    captain_id,
    department,
    shift,
    semester,
    captain_name,
    student_id,
    phone,
    email,
    session_year,
    captain_rank
FROM class_captains
WHERE institution_id = 1
  AND is_active = true
  AND semester = 3
ORDER BY department, shift, captain_rank
LIMIT 100;


Example 7:

User Query:
"আমার ক্লাসের ক্যাপ্টেন কে?"

IMPORTANT:

If the query does not contain enough information to identify
the class (department, shift, semester), do NOT guess the class.

The SQL generator should only generate a specific class query
when the required class identifiers are available from the input.

==================================================
CAPTAIN LIMIT RULE
==================================================

For a specific class:

LIMIT 10

For department + semester:

LIMIT 20

For broad captain listing:

LIMIT 100

If the user explicitly requests a number N,
use that number as LIMIT N.

==================================================
CAPTAIN QUERY VALIDATION
==================================================

Before returning a captain query, verify:

✓ FROM class_captains is present
✓ institution_id = 1 is present
✓ is_active = true is present unless inactive/former captains are requested
✓ Correct department filter is present when department is specified
✓ Correct semester filter is present when semester is specified
✓ Correct shift filter is present when shift is specified
✓ Correct captain_rank filter is present when rank is explicitly requested
✓ captain_name is selected
✓ Relevant contact fields are selected when requested
✓ ORDER BY is appropriate
✓ LIMIT is present
✓ PostgreSQL syntax is valid
✓ temporal_analysis is NOT used for captain queries"""),
    ("human", "User Query: {user_query}\n\nGenerate the SQL query:")
])


def sql_query_create_node(state: RAGState) -> dict:
    """
    Generate SQL query to retrieve notices from the notices table.
    
    Analyzes user query to determine:
    - Single latest notice vs multiple notices
    - Number of notices to retrieve
    - Category filtering (if any)
    
    Only generates SQL - does NOT execute it.
    Execution happens in sql_query_db_call_node.
    """
    sql_query_state = state.get("sql_query", {})

    # Use normalized_query as input
    user_query = state.get("normalized_query") or state.get("user_input", "")

    if not user_query:
        return {
            "sql_query": {
                **sql_query_state,
                "query_str": "",
                "final_answer": "দয়া করে আপনার প্রশ্নটি লিখুন।"
            }
        }

    try:
        print(f"[sql_query_create] Generating SQL for: {user_query}")
        
        # Get LLM and create chain
        llm = get_llm()
        sql_chain = _SQL_GENERATION_PROMPT | llm
        
        # Generate SQL query
        response = sql_chain.invoke({"user_query": user_query})
        sql_query_raw = extract_content(response).strip()
        
        # Extract SQL from code block if present
        sql_query = sql_query_raw
        if "```sql" in sql_query:
            sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql_query:
            sql_query = sql_query.split("```")[1].split("```")[0].strip()
        
        # Basic validation
        if not sql_query or "SELECT" not in sql_query.upper():
            raise ValueError("Invalid SQL query generated")
        
        # Flexible validation - allow any table (notices, class_captains, teachers, etc.)
        sql_upper = sql_query.upper()
        
        # ★ FIX: Only add ORDER BY for notices table if COMPLETELY missing
        if "FROM NOTICES" in sql_upper:
            if "ORDER BY" not in sql_upper:
                # No ORDER BY at all - add it
                print("[WARNING] Missing ORDER BY for notices table, adding it")
                if "LIMIT" in sql_upper:
                    sql_query = sql_query.replace("LIMIT", "ORDER BY created_at DESC LIMIT")
                else:
                    sql_query += " ORDER BY created_at DESC LIMIT 1"
            elif "ORDER BY CREATED_AT DESC" not in sql_upper:
                # Has ORDER BY but wrong column - replace it
                print("[WARNING] Wrong ORDER BY column for notices, fixing it")
                import re
                # Replace ORDER BY <anything> with ORDER BY created_at DESC
                sql_query = re.sub(
                    r'ORDER\s+BY\s+\w+\s+(DESC|ASC)?',
                    'ORDER BY created_at DESC',
                    sql_query,
                    flags=re.IGNORECASE
                )
        
        print(f"[sql_query_create] Generated SQL:\n{sql_query}")
        print(f"[sql_query_create] SQL query ready for execution by db_call node")
        
        return {
            "sql_query": {
                **sql_query_state,
                "query_str": sql_query,
                "query_type": "notices_query",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    except Exception as e:
        error_msg = f"SQL generation error: {str(e)}"
        print(f"[sql_query_create] {error_msg}")
        import traceback
        traceback.print_exc()

        return {
            "sql_query": {
                **sql_query_state,
                "query_str": "",
                "final_answer": f"SQL query তৈরিতে সমস্যা হয়েছে: {str(e)}"
            }
        }



# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    state = {
        "user_input": "latest notice dao",
        "normalized_query": "latest notice dao",
        "sql_query": {"short_info": False, "not_possible": False}
    }

    result = sql_query_create_node(state)
    print("\nSQL Query Create Result:")
    sql_state = result.get("sql_query", {})
    print(f"  Query Type: {sql_state.get('query_type')}")
    print(f"  Generated SQL:\n{sql_state.get('query_str')}")
    print(f"  Generated at: {sql_state.get('generated_at')}")
