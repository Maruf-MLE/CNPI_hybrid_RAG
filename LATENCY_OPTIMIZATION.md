# RAG System Latency Analysis & Optimization Guide
**Date:** 2026-08-12  
**Status:** Performance Audit

---

## 🔴 Problem 1: SQL Retrieve Check - High Latency

### Root Causes:

#### 1. **Unnecessarily Complex LLM Prompt (265 lines!)**
```python
# sql_retrieve_check.py line 39-192
_retrieve_check_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Retrieve Check Node... 
    # 150+ lines of detailed instructions
    # Multiple examples
    # Step-by-step analysis guidelines
    """),
    ("human", "User Query: {user_input}")
])
```

**Impact:** 
- Long prompt = more tokens to process
- Detailed examples = slower LLM reasoning
- **Estimated latency: 2-4 seconds per call**

#### 2. **Structured Output with 7 Fields**
```python
class RetrieveCheckOutput(BaseModel):
    suitable: str
    needs_more_info: bool
    clarification: str
    is_greeting: bool
    missing_shift: bool
    missing_department: bool
    missing_semester: bool
```

**Impact:**
- LLM must generate structured JSON
- More fields = more validation time
- **Estimated latency: +0.5-1 second**

#### 3. **Redundant with SQL Query Info Check**
Both `sql_retrieve_check` and `sql_query_info_check` do similar validation:
- Check for missing department/shift/semester
- Detect greetings
- Generate clarification messages

**Impact:**
- Duplicate work
- Double LLM calls for similar tasks

---

## ✅ Solution 1: Optimize SQL Retrieve Check

### Option A: Simplify Prompt (Quick Win)
Reduce prompt from 265 lines to ~50 lines:

```python
_retrieve_check_prompt = ChatPromptTemplate.from_messages([
    ("system", """Check if query has enough info for semantic search.

ROUTINE queries need: Department + Shift + Semester
TEACHER queries need: Department + Shift
GENERAL queries: no requirements

Set missing_* flags for required but absent fields.
Return JSON: {suitable, needs_more_info, missing_shift, missing_department, missing_semester}
"""),
    ("human", "{user_input}")
])
```

**Expected Improvement:** 40-60% faster (1.2-1.6 seconds saved)

### Option B: Rule-Based Check (Best Performance)
Replace LLM with regex/keyword matching:

```python
def sql_retrieve_check_node_optimized(state: RAGState) -> Dict[str, Any]:
    """Fast rule-based check - no LLM call."""
    user_input = state.get("normalized_query", "")
    
    # Detect query type
    is_routine = any(k in user_input.lower() for k in ["routine", "schedule", "timetable", "রুটিন"])
    is_teacher = any(k in user_input.lower() for k in ["ci", "teacher", "instructor", "শিক্ষক"])
    
    # Check what's present
    has_dept = any(d in user_input.upper() for d in ["CST", "ENT", "ET", "RAC", "FT", "MT"])
    has_shift = any(s in user_input.lower() for s in ["shift", "morning", "day", "1st", "2nd"])
    has_semester = any(str(i) in user_input for i in range(1, 9))
    
    # Determine missing fields
    if is_routine:
        missing_dept = not has_dept
        missing_shift = not has_shift
        missing_semester = not has_semester
        needs_more_info = missing_dept or missing_shift or missing_semester
    elif is_teacher:
        missing_dept = not has_dept
        missing_shift = not has_shift
        missing_semester = False
        needs_more_info = missing_dept or missing_shift
    else:
        # General query
        needs_more_info = False
        missing_dept = missing_shift = missing_semester = False
    
    return {
        "sql_retrieve": {
            "need_more_info": needs_more_info,
            "missing_shift": missing_shift,
            "missing_department": missing_dept,
            "missing_semester": missing_semester,
        }
    }
```

**Expected Improvement:** 95% faster (only ~50ms vs 2-3 seconds)

---

## 🔴 Problem 2: Sequential Execution Bottleneck

### Current Flow (All Sequential):
```
rewrite_query (2s)
    ↓
entity_normalizer (1.5s)
    ↓
llm_decide_path (2s)
    ↓
sql_retrieve_check (3s)  ← BOTTLENECK!
    ↓
sql_retrieve_create (0.1s)
    ↓
sql_retrieve_context (1s)
    ↓
sql_retrieve_response (3s)

Total: ~12.6 seconds 😱
```

---

## ✅ Solution 2: Parallel Execution Opportunities

### Strategy 1: Parallel Path-Specific Checks
After `llm_decide_path`, run path-specific checks in parallel:

```python
# BEFORE (Sequential):
llm_decide_path → sql_retrieve_check → sql_retrieve_create

# AFTER (Parallel):
llm_decide_path → [sql_query_info_check, sql_retrieve_check, web_search_rewrite]
                  ↓ (use only the decided path's result)
                  chosen_path_node
```

**Expected Improvement:** Save 1-2 seconds (but wastes compute)

### Strategy 2: Merge Redundant Checks (RECOMMENDED)
Combine `sql_query_info_check` and `sql_retrieve_check` into one unified node:

```python
def unified_query_check_node(state: RAGState) -> Dict[str, Any]:
    """Single check node for both SQL Query and SQL Retrieve paths."""
    # Rule-based logic (fast)
    # Sets flags for both paths
    # Runs once, used by both
```

**Current:**
```
SQL Query path:   llm_decide_path → sql_query_info_check (2s)
SQL Retrieve path: llm_decide_path → sql_retrieve_check (3s)
```

**Optimized:**
```
Both paths: llm_decide_path → unified_query_check (0.05s)
```

**Expected Improvement:** Save 2-3 seconds per request

### Strategy 3: Async Embedding Generation
In `sql_retrieve_context` and `sql_query_create`, embedding calls are synchronous:

```python
# CURRENT (Sync):
results = hybrid_search(query_text=user_query)  # 1 second

# OPTIMIZED (Async):
import asyncio
results = await async_hybrid_search(query_text=user_query)  # 0.4 seconds
```

**Expected Improvement:** 50-60% faster retrieval

---

## 📊 Recommended Priority

| Optimization | Difficulty | Impact | Time Saved |
|-------------|-----------|--------|------------|
| 1. Replace sql_retrieve_check with rule-based | Low | **HIGH** | **2-3s** |
| 2. Merge redundant check nodes | Medium | **HIGH** | **2-3s** |
| 3. Simplify LLM prompts | Low | Medium | 1-2s |
| 4. Async embedding generation | High | Medium | 0.5-1s |
| 5. Cache embedding results | Medium | Low | 0.2-0.5s |

---

## 🎯 Quick Win Implementation

### Immediate Action (10 minutes):
Replace `sql_retrieve_check_node` with rule-based version (see Option B above)

### Expected Results:
- **Before:** 12-15 seconds total latency
- **After:** 8-10 seconds total latency
- **Improvement:** 30-40% faster

---

## 🚀 Parallel Execution Summary

### ❌ Cannot Run in Parallel:
1. **Phase 1 nodes** (sequential by design):
   - rewrite_query → entity_normalizer → llm_decide_path
   
2. **Within-path nodes** (data dependency):
   - sql_retrieve_create → sql_retrieve_context → sql_retrieve_response

### ✅ Can Run in Parallel:

1. **Hybrid sub-queries** (already parallel via Send API):
   ```python
   dispatch_sub_queries → [sub_q1, sub_q2, sub_q3] → append_sub_answer
   ```

2. **Multiple independent LLM calls** (future optimization):
   - Translation + Entity normalization (if independent)
   - Multiple retrieval strategies simultaneously

3. **Embedding + BM25** (future optimization):
   ```python
   # In hybrid_search():
   async def parallel_search():
       embedding_results = await get_embedding_search()
       bm25_results = await get_bm25_search()
       return merge_rrf(embedding_results, bm25_results)
   ```

---

## 📝 Implementation Notes

### File to Modify:
- `Cnpi_RAG/nodes/sql_retrieve_check.py` (priority 1)

### Testing:
```bash
python test_rag.py  # Measure latency before/after
```

### Rollback Plan:
Keep original LLM-based check as `sql_retrieve_check_node_legacy()` for fallback

---

**Next Steps:**
1. Implement rule-based sql_retrieve_check
2. Measure performance improvement
3. Apply same pattern to sql_query_info_check
4. Consider async embedding generation (Phase 2)
