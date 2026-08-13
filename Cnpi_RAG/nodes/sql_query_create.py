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


# SQL Query Generation Prompt for Notices Table
_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an SQL Query Generation Expert for the CNPI College Database.

Your ONLY task is to generate PostgreSQL queries to retrieve notices from the notices table.

==================================================
DATABASE SCHEMA — notices table
==================================================

CREATE TABLE notices(
    notice_id SERIAL NOT NULL PRIMARY KEY,
    institution_id INTEGER NOT NULL,
    category VARCHAR(60),
    title_bn TEXT NOT NULL,
    content_bn TEXT NOT NULL,
    faq_bn TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT notices_institution_id_fkey FOREIGN KEY(institution_id) 
        REFERENCES institutions(institution_id)
);

CREATE INDEX idx_notices_category ON public.notices USING btree (category);

COLUMN DESCRIPTIONS:
- notice_id: Unique identifier for each notice
- institution_id: Foreign key to institutions table (CNPI = 1)
- category: Notice category (e.g., 'Attendance', 'Exam', 'Academic', 'Admission')
- title_bn: Notice title in Bengali
- content_bn: Notice content in Bengali (MAIN FIELD TO RETRIEVE)
- faq_bn: Optional FAQ content in Bengali
- created_at: Notice creation timestamp (USE THIS FOR ORDERING)

==================================================
QUERY TYPES YOU MUST HANDLE
==================================================

1. LATEST NOTICE (single most recent):
   Keywords: "latest notice", "সর্বশেষ নোটিশ", "শেষ নোটিশ", "last notice"
   
   SQL Pattern:
   SELECT notice_id, title_bn, content_bn, category, created_at 
   FROM notices 
   WHERE institution_id = 1 
   ORDER BY created_at DESC 
   LIMIT 1;

2. LAST N NOTICES (multiple recent notices):
   Keywords: "last 5 notices", "সর্বশেষ ৫টি নোটিশ", "শেষ ৫টি", "last N notices"
   
   SQL Pattern:
   SELECT notice_id, title_bn, content_bn, category, created_at 
   FROM notices 
   WHERE institution_id = 1 
   ORDER BY created_at DESC 
   LIMIT N;
   
   Extract N from query (common values: 3, 5, 10)

3. CATEGORY-SPECIFIC NOTICES:
   Keywords: "exam notice", "admission notice", "পরীক্ষার নোটিশ"
   
   SQL Pattern:
   SELECT notice_id, title_bn, content_bn, category, created_at 
   FROM notices 
   WHERE institution_id = 1 
       AND category ILIKE '%keyword%'
   ORDER BY created_at DESC 
   LIMIT N;

==================================================
CRITICAL SQL GENERATION RULES
==================================================

1. ALWAYS include:
   - WHERE institution_id = 1 (filter for CNPI)
   - ORDER BY created_at DESC (newest first)
   - LIMIT clause (1 for single, N for multiple)

2. ALWAYS select these columns:
   - notice_id
   - title_bn
   - content_bn (MOST IMPORTANT - contains notice text)
   - category
   - created_at (for date display)

3. DO NOT select:
   - institution_id (already filtered)
   - faq_bn (unless specifically asked)

4. Use ILIKE for case-insensitive text matching in category
5. Default LIMIT is 1 for "latest" and 5 for "last N" if N is unclear

==================================================
NUMBER EXTRACTION
==================================================

Bengali numbers → English:
- ৫ → 5
- ১০ → 10
- ৩ → 3

Extract from patterns like:
- "last 5 notices" → 5
- "সর্বশেষ ৫টি" → 5
- "শেষ ১০টি নোটিশ" → 10

==================================================
EXAMPLES
==================================================

Query: "latest notice dao"
SQL:
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 1;
```

Query: "সর্বশেষ ৫টি নোটিশ দেখাও"
SQL:
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 5;
```

Query: "CNPI er last 10 notices"
SQL:
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 10;
```

Query: "exam related latest notice"
SQL:
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
    AND category ILIKE '%exam%'
ORDER BY created_at DESC 
LIMIT 1;
```

==================================================
OUTPUT FORMAT (CRITICAL)
==================================================

Return ONLY the SQL query wrapped in a code block:

```sql
SELECT ...
```

DO NOT include:
- Explanations
- Comments
- Additional text
- Python code
- Conversational responses

Just the raw SQL query in a code block.

==================================================
FINAL CHECKLIST
==================================================

Before returning, verify:
✓ WHERE institution_id = 1 is present
✓ ORDER BY created_at DESC is present
✓ LIMIT clause is present
✓ SELECT includes: notice_id, title_bn, content_bn, category, created_at
✓ Query is valid PostgreSQL syntax
✓ Query is wrapped in ```sql code block

Your output must be executable SQL ONLY."""),
    ("human", "User Query: {user_query}\n\nGenerate the SQL query:")
])


def sql_query_create_node(state: RAGState) -> dict:
    """
    Generate SQL query to retrieve notices from the notices table and execute it.
    
    Analyzes user query to determine:
    - Single latest notice vs multiple notices
    - Number of notices to retrieve
    - Category filtering (if any)
    
    Generates SQL, executes it, and returns formatted context.
    """
    sql_query_state = state.get("sql_query", {})

    # Use normalized_query as input
    user_query = state.get("normalized_query") or state.get("user_input", "")

    if not user_query:
        return {
            "sql_query": {
                **sql_query_state,
                "query_str": "",
                "raw_context": "",
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
        
        # Ensure critical components are present
        sql_upper = sql_query.upper()
        if "FROM NOTICES" not in sql_upper:
            raise ValueError("Query must target notices table")
        if "ORDER BY CREATED_AT DESC" not in sql_upper:
            print("[WARNING] Missing ORDER BY created_at DESC, adding it")
            if "LIMIT" in sql_upper:
                sql_query = sql_query.replace("LIMIT", "ORDER BY created_at DESC LIMIT")
            else:
                sql_query += " ORDER BY created_at DESC LIMIT 1"
        
        print(f"[sql_query_create] Generated SQL:\n{sql_query}")
        
        # ★ EXECUTE THE SQL QUERY
        print(f"[sql_query_create] Executing SQL query...")
        results = execute_query(sql_query, fetch=True)
        
        if not results or len(results) == 0:
            print(f"[sql_query_create] No results found")
            return {
                "sql_query": {
                    **sql_query_state,
                    "query_str": sql_query,
                    "query_type": "notices_query",
                    "row_count": 0,
                    "raw_context": "",
                    "contexts": [],
                    "context_found": False,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "final_answer": "দুঃখিত, কোনো নোটিশ পাওয়া যায়নি।"
                }
            }
        
        print(f"[sql_query_create] Retrieved {len(results)} notice(s)")
        
        # ★ FORMAT THE RESULTS AS CONTEXT
        raw_context_parts = []
        processed_contexts = []
        
        for i, row in enumerate(results, 1):
            # Raw context for debugging
            raw_context_parts.append(f"--- Notice {i} ---")
            row_str = ", ".join(f"{k}: {str(v) if v is not None else 'NULL'}" for k, v in row.items())
            raw_context_parts.append(row_str)
            
            # Processed context for LLM
            context_data = {
                "rank": i,
                "notice_id": row.get("notice_id"),
                "title_bn": row.get("title_bn", ""),
                "content_bn": row.get("content_bn", ""),
                "category": row.get("category", ""),
                "created_at": str(row.get("created_at", "")),
            }
            processed_contexts.append(context_data)
            
            # Log preview
            title_preview = str(context_data["title_bn"])[:50]
            print(f"  [{i}] Notice: {title_preview}... (Created: {context_data['created_at']})")
        
        raw_context = "\n".join(raw_context_parts)
        
        return {
            "sql_query": {
                **sql_query_state,
                "query_str": sql_query,
                "query_type": "notices_query",
                "row_count": len(results),
                "raw_context": raw_context,
                "contexts": processed_contexts,
                "context_found": True,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    except Exception as e:
        error_msg = f"SQL generation/execution error: {str(e)}"
        print(f"[sql_query_create] {error_msg}")
        import traceback
        traceback.print_exc()

        return {
            "sql_query": {
                **sql_query_state,
                "query_str": "",
                "row_count": 0,
                "raw_context": "",
                "contexts": [],
                "context_found": False,
                "final_answer": f"নোটিশ খোঁজায় সমস্যা হয়েছে: {str(e)}"
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
