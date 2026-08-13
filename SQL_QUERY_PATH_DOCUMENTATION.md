# SQL Query Path Documentation

## Overview

SQL Query Path এখন **notices table থেকে latest/last N notices retrieve** করার জন্য configured করা হয়েছে।

---

## Complete Flow Diagram

```
User Query: "latest notice dao"
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 1. Entry Node (entry.py)                                      │
│    - Rewrite query for better understanding                   │
│    - Context resolution from chat history                     │
│    Output: rewritten_query                                    │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 2. Router Node (router.py)                                    │
│    - Decides which path to take                               │
│    - Checks for "latest notice" / "last N notices" keywords   │
│    Output: decided_path = "sql_query"                         │
│            confidence_score = 0.95                            │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 3. Info Check Node (sql_query_info_check.py)                 │
│    - Validates if query has sufficient information            │
│    - For notices: usually sufficient (no dept/shift needed)   │
│    Output: short_info = false                                 │
│            not_possible = false                               │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 4. SQL Query Create Node (sql_query_create.py) ★ NEW ★       │
│    - LLM generates SQL query for notices table                │
│    - Extracts number (5, 10, etc.) from query                 │
│    - Adds proper filtering & ordering                         │
│    Output: query_str = "SELECT notice_id, title_bn,           │
│                         content_bn, category, created_at      │
│                         FROM notices                          │
│                         WHERE institution_id = 1              │
│                         ORDER BY created_at DESC              │
│                         LIMIT N;"                             │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 5. DB Call Node (sql_query_db_call.py)                       │
│    - Executes the generated SQL query                         │
│    - Retrieves actual data from PostgreSQL                    │
│    Output: row_count = N                                      │
│            raw_context = "--- Row 1 ---                       │
│                          notice_id: 123,                      │
│                          title_bn: ...,                       │
│                          content_bn: ...,                     │
│                          created_at: 2026-08-10..."           │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 6. Row Check Node (sql_query_row_check.py)                   │
│    - row_count = 0 → fallback to sql_retrieve path           │
│    - row_count = 1 → directly to response                    │
│    - row_count > 1 → optimize/merge context first            │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│ 7. Response Node (sql_query_response.py) ★ UPDATED ★         │
│    - LLM formats the notice data beautifully                  │
│    - Applies notice-specific formatting rules                 │
│    - Adds emojis, bold text, proper structure                 │
│    Output: final_answer = "📢 **[Title]**                     │
│                            📅 তারিখ: [Date]                   │
│                            [Content]"                         │
└────────────────────────────────────────────────────────────────┘
         ↓
    Final Answer to User
```

---

## Key Files Modified

### 1. **sql_query_create.py** (Major Changes)
**Location:** `Cnpi_RAG/nodes/sql_query_create.py`

**Changes:**
- ❌ Removed: Hybrid search (embedding + BM25)
- ✅ Added: LLM-based SQL query generation
- ✅ Added: Comprehensive prompt for notices table
- ✅ Added: Number extraction (Bengali → English: ৫ → 5)
- ✅ Added: SQL validation & safety checks

**Prompt Structure:**
```
- Database schema (notices table)
- Query types (latest, last N, category-specific)
- SQL generation rules (LIMIT, ORDER BY, WHERE)
- Number extraction logic
- Output format requirements
```

**Example Output:**
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 5;
```

---

### 2. **sql_query_response.py** (Enhanced)
**Location:** `Cnpi_RAG/nodes/sql_query_response.py`

**Changes:**
- ✅ Added: Notice-specific formatting rules
- ✅ Added: Date conversion guidelines
- ✅ Added: Emoji usage for notices (📢, 📅, 📋)
- ✅ Added: Multi-notice presentation format
- ✅ Enhanced: Bengali language support

**Notice Format:**
```markdown
📢 **[Notice Title]**
📅 তারিখ: [Date in readable format]
📋 বিভাগ: [Category]

[Full notice content]

---
```

---

## Router Configuration

**File:** `Cnpi_RAG/nodes/router.py` (Lines 75-120)

**SQL Query Path Triggers:**
```
✅ "latest notice"
✅ "সর্বশেষ নোটিশ"
✅ "last 5 notices"
✅ "শেষ ৫টি নোটিশ"
✅ "CNPI latest notice"
✅ Any variation asking for recent notices
```

**Other CNPI queries go to:** `sql_retrieve` path (hybrid search)

---

## Database Schema

### Notices Table Structure

```sql
CREATE TABLE notices(
    notice_id SERIAL NOT NULL PRIMARY KEY,
    institution_id INTEGER NOT NULL,
    category VARCHAR(60),
    title_bn TEXT NOT NULL,
    content_bn TEXT NOT NULL,       -- ★ Main content field
    faq_bn TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),  -- ★ Used for ordering
    CONSTRAINT notices_institution_id_fkey 
        FOREIGN KEY(institution_id) REFERENCES institutions(institution_id)
);

CREATE INDEX idx_notices_category ON public.notices USING btree (category);
```

**Key Fields:**
- `content_bn`: Notice এর main content (Bengali text)
- `created_at`: Timestamp for ordering (newest first)
- `institution_id`: Filter by institution (CNPI = 1)
- `category`: Notice type (Attendance, Exam, Academic, Admission)

---

## Testing

### Quick Test Script
**File:** `test_sql_notice_query.py`

**Usage:**
```bash
python test_sql_notice_query.py
```

**Test Cases:**
1. "latest notice dao"
2. "সর্বশেষ নোটিশ দেখাও"
3. "CNPI er last 5 notices"
4. "শেষ ৫টি নোটিশ"
5. "last notice"

**Test Flow:**
- ✅ Entry → Rewrite
- ✅ Router → Path decision
- ✅ Info Check → Validation
- ✅ SQL Create → Query generation
- ✅ DB Call → Execution
- ✅ Response → Formatting

---

## Example Queries & Expected Behavior

### Example 1: Single Latest Notice
**Input:** `"latest notice dao"`

**Generated SQL:**
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 1;
```

**Expected Output:**
```
📢 **ভর্তি বিজ্ঞপ্তি - ২০২৬**
📅 তারিখ: 10 August, 2026
📋 বিভাগ: ভর্তি সংক্রান্ত

চাঁপাইনবাবগঞ্জ পলিটেকনিক ইনস্টিটিউটে ২০২৬-২৭ শিক্ষাবর্ষে 
ডিপ্লোমা ইন ইঞ্জিনিয়ারিং কোর্সে ভর্তি চলছে...

[Full content here]
```

---

### Example 2: Last 5 Notices
**Input:** `"সর্বশেষ ৫টি নোটিশ দেখাও"`

**Generated SQL:**
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 5;
```

**Expected Output:**
```
📢 **নোটিশ ১:** ভর্তি বিজ্ঞপ্তি
📅 তারিখ: 10 August, 2026

[Content 1]

---

📢 **নোটিশ ২:** পরীক্ষার সময়সূচী
📅 তারিখ: 05 August, 2026

[Content 2]

---

[... 3 more notices ...]
```

---

### Example 3: Category-Specific
**Input:** `"exam related latest notice"`

**Generated SQL:**
```sql
SELECT notice_id, title_bn, content_bn, category, created_at 
FROM notices 
WHERE institution_id = 1 
    AND category ILIKE '%exam%'
ORDER BY created_at DESC 
LIMIT 1;
```

---

## Prompts Location

**All prompts are embedded in code files** (not external files):

1. **Entry Rewrite Prompt:** `Cnpi_RAG/nodes/entry.py` (Lines 27-720)
2. **Router Prompt:** `Cnpi_RAG/nodes/router.py` (Lines 34-455)
3. **Info Check Prompt:** `Cnpi_RAG/nodes/sql_query_info_check.py` (Lines 36-190)
4. **SQL Generation Prompt:** `Cnpi_RAG/nodes/sql_query_create.py` (Lines 26-170) ★ NEW
5. **Response Prompt:** `Cnpi_RAG/nodes/sql_query_response.py` (Lines 26-120) ★ UPDATED

**Note:** `Cnpi_RAG/prompts/node_prompts.py` exists but is **NOT used** in current system.

---

## Debugging Tips

### Check SQL Generation
```python
from Cnpi_RAG.nodes.sql_query_create import sql_query_create_node

state = {
    "normalized_query": "latest notice dao",
    "sql_query": {}
}

result = sql_query_create_node(state)
print(result["sql_query"]["query_str"])
```

### Check Database Connection
```python
from Cnpi_RAG.utils.db_utils import execute_query

query = """
SELECT notice_id, title_bn, created_at 
FROM notices 
WHERE institution_id = 1 
ORDER BY created_at DESC 
LIMIT 1;
"""

results = execute_query(query, fetch=True)
print(results)
```

### Enable Verbose Logging
```python
# Add to your test script
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Troubleshooting

### Issue: Router not selecting sql_query path
**Solution:** Check router prompt in `router.py:34-455`. Ensure query contains notice keywords.

### Issue: SQL query generation fails
**Solution:** Check LLM connection in `utils/llm_utils.py`. Verify API keys in `.env`.

### Issue: No data returned from database
**Solution:** 
1. Check if notices table has data: `SELECT COUNT(*) FROM notices WHERE institution_id = 1;`
2. Verify `institution_id = 1` is correct for CNPI
3. Check database connection in `utils/db_utils.py`

### Issue: Response formatting incorrect
**Solution:** Check prompt in `sql_query_response.py:26-120`. Ensure notice-specific rules are present.

---

## Future Enhancements

### Potential Improvements:
1. ✨ Add date range filtering ("last week's notices")
2. ✨ Add full-text search in content_bn
3. ✨ Add pagination for large result sets
4. ✨ Add notice priority/urgency handling
5. ✨ Add department-specific notice filtering
6. ✨ Cache frequently accessed notices

---

## Summary

✅ **SQL Query Path now working for notices table**
✅ **LLM generates proper PostgreSQL queries**
✅ **Retrieves data using created_at DESC ordering**
✅ **Beautiful formatting with emojis and structure**
✅ **Full Bengali language support**
✅ **Test script available for validation**

**Test Command:**
```bash
python test_sql_notice_query.py
```

---

Last Updated: 2026-08-13
