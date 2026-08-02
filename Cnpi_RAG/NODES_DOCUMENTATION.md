# CNPI Hybrid RAG — সম্পূর্ণ Node Documentation

> **প্রজেক্ট:** Chandpur Govt. Polytechnic Institute (CNPI) Hybrid RAG System  
> **Framework:** LangGraph (StateGraph)  
> **তারিখ:** 2026-07-21  

---

## সিস্টেম সংক্ষেপ

এই RAG সিস্টেমটি ৫টি Phase-এ বিভক্ত এবং মোট **২৬টি Node** দিয়ে তৈরি। ব্যবহারকারীর প্রশ্ন গ্রহণ করে সঠিক path নির্বাচন করে উত্তর দেয়।

### ৪টি Retrieval Path:
| Path | কাজ |
|------|-----|
| `sql_query` | Structured SQL দিয়ে নির্দিষ্ট তথ্য খোঁজে |
| `sql_retrieve` | Embedding + BM25 hybrid search দিয়ে semantic তথ্য খোঁজে |
| `web_search` | DuckDuckGo দিয়ে ইন্টারনেট থেকে তথ্য আনে |
| `hybrid` | জটিল প্রশ্নকে sub-questions-এ ভেঙে parallel-এ সব path চালায় |

---

## Phase 1 — Entry & Router (২টি Node)

---

### Node 1: `rewrite_query`
**ফাইল:** `nodes/entry.py` | **Function:** `rewrite_query_node`

**কাজের বিবরণ:**
ব্যবহারকারীর কাঁচা প্রশ্নটি LLM দিয়ে পুনরায় লেখে (rewrite) যাতে database search, semantic retrieval এবং user intent ভালোভাবে ধরা যায়। Bengali/Banglish ভাষা সংরক্ষণ করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | ব্যবহারকারীর মূল প্রশ্ন |
| **Output** | `rewritten_query` | `str` | LLM দ্বারা rewrite করা পরিষ্কার প্রশ্ন |

**পরবর্তী Node:** → `llm_decide_path`

---

### Node 2: `llm_decide_path`
**ফাইল:** `nodes/router.py` | **Function:** `llm_decide_path_node`

**কাজের বিবরণ:**
Rewritten query বিশ্লেষণ করে কোন retrieval path ব্যবহার করতে হবে তা LLM-এর structured output দিয়ে নির্ধারণ করে। Confidence score < 0.7 হলে সরাসরি `hybrid` path-এ পাঠায়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `rewritten_query` | `str` | Phase 1 এর rewrite করা প্রশ্ন |
| **Output** | `decided_path` | `str` | `"sql_query"` / `"sql_retrieve"` / `"web_search"` / `"hybrid"` |
| **Output** | `confidence_score` | `float` | 0.0 – 1.0 এর মধ্যে router এর নিশ্চয়তার মান |

**Routing Rules:**
- `confidence_score < 0.7` → `hybrid_depth_check`
- `decided_path = "sql_query"` → `sql_query_info_check`
- `decided_path = "sql_retrieve"` → `sql_retrieve_check`
- `decided_path = "web_search"` → `web_search_rewrite`
- `decided_path = "hybrid"` → `hybrid_depth_check`

---

## Phase 2 — SQL Query Path (৮টি Node)

> **উদ্দেশ্য:** নির্দিষ্ট তথ্যের জন্য SQL query তৈরি করে PostgreSQL database থেকে ডেটা আনে।  
> **Database Tables:** `departments`, `teachers`, `students`, `notices`

---

### Node 3: `sql_query_info_check`
**ফাইল:** `nodes/sql_query_info_check.py` | **Function:** `sql_query_info_check_node`

**কাজের বিবরণ:**
SQL দিয়ে প্রশ্নের উত্তর দেওয়া সম্ভব কিনা এবং প্রশ্নে যথেষ্ট তথ্য আছে কিনা তা যাচাই করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Output** | `sql_query.short_info` | `bool` | `True` = প্রশ্ন অস্পষ্ট, আরো তথ্য দরকার |
| **Output** | `sql_query.not_possible` | `bool` | `True` = SQL দিয়ে উত্তর দেওয়া সম্ভব নয় |
| **Output** | `sql_query.final_answer` | `str` | Error বা clarification message (শুধু short_info/not_possible এ) |

**Routing:**
- `short_info=True` বা `not_possible=True` → `sql_query_short_info_response`
- অন্যথায় → `sql_query_create`

---

### Node 4: `sql_query_short_info_response`
**ফাইল:** `nodes/sql_query_short_info_response.py` | **Function:** `sql_query_short_info_response_node`

**কাজের বিবরণ:**
Query অস্পষ্ট বা impossible হলে LLM ব্যবহার করে database schema দেখে স্মার্ট clarification message তৈরি করে। User এর ভাষায় (বাংলা/ইংরেজি) উত্তর দেয়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Input** | `sql_query.short_info` | `bool` | অস্পষ্ট প্রশ্নের flag |
| **Input** | `sql_query.not_possible` | `bool` | Impossible প্রশ্নের flag |
| **Output** | `final_answer` | `str` | Top-level clarification বা apology message |
| **Output** | `answer_status` | `str` | `"need_more_info"` বা `"not_found"` |

**পরবর্তী Node:** → `sub_query_router_node`

---

### Node 5: `sql_query_create`
**ফাইল:** `nodes/sql_query_create.py` | **Function:** `sql_query_create_node`

**কাজের বিবরণ:**
Natural language প্রশ্নকে PostgreSQL SQL query-তে রূপান্তর করে। Markdown formatting ছাড়া শুধু raw SQL return করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Input** | `sql_query.short_info` | `bool` | অস্পষ্ট flag |
| **Output** | `sql_query.query_str` | `str` | তৈরি SQL query string |

**পরবর্তী Node:** → `sql_query_db_call`

---

### Node 6: `sql_query_db_call`
**ফাইল:** `nodes/sql_query_db_call.py` | **Function:** `sql_query_db_call_node`

**কাজের বিবরণ:**
তৈরি SQL query PostgreSQL database-এ execute করে raw results আনে। Single row এবং multiple rows উভয়কেই text format-এ সাজায়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `sql_query.query_str` | `str` | Execute করার SQL |
| **Output** | `sql_query.row_count` | `int` | কতটি row ফেরত এসেছে |
| **Output** | `sql_query.raw_context` | `str` | Database থেকে আসা raw text context |

**পরবর্তী Node:** → `sql_query_row_check`

---

### Node 7: `sql_query_row_check`
**ফাইল:** `nodes/sql_query_row_check.py` | **Function:** `sql_query_row_check_node`

**কাজের বিবরণ:**
Database থেকে আসা row count যাচাই করে routing এর জন্য প্রস্তুত করে। নিজে কোনো state পরিবর্তন করে না, শুধু diagnostic print করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `sql_query.row_count` | `int` | DB থেকে আসা row সংখ্যা |
| **Output** | `{}` | `dict` | কোনো state পরিবর্তন নেই |

**Routing (graph.py তে):**
- `row_count = 0` → `fallback_dispatcher`
- `row_count = 1` → `sub_query_router_node`
- `row_count > 1` → `sql_query_optimize`

---

### Node 8: `sql_query_optimize`
**ফাইল:** `nodes/sql_query_optimize.py` | **Function:** `sql_query_optimize_node`

**কাজের বিবরণ:**
শুধুমাত্র `row_count > 1` হলে চালু হয়। Multiple DB rows-কে একটি structured, LLM-friendly context string-এ merge করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `sql_query.raw_context` | `str` | Multiple rows এর raw text |
| **Input** | `sql_query.row_count` | `int` | Row সংখ্যা |
| **Output** | `sql_query.optimized_context` | `str` | LLM-এর জন্য সাজানো structured context |

**পরবর্তী Node:** → `sub_query_router_node`

---

### Node 9: `fallback_dispatcher`
**ফাইল:** `nodes/fallback_dispatcher.py` | **Function:** `fallback_dispatcher_node`

**কাজের বিবরণ:**
SQL Query path-এ `row_count = 0` হলে এই node SQL Query থেকে SQL Retrieve path-এ bridge করে। `decided_path` এবং `sql_retrieve` state reset করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | *(state থেকে implicit)* | — | row_count=0 এর পর call হয় |
| **Output** | `decided_path` | `str` | `"sql_retrieve"` তে সেট করা হয় |
| **Output** | `sql_retrieve` | `dict` | Fresh empty state |

**পরবর্তী Node:** → `sql_retrieve_check`

---

### Node 10: `sql_query_response`
**ফাইল:** `nodes/sql_query_response.py` | **Function:** `sql_query_response_node`

**কাজের বিবরণ:**
Optimized database context এবং user এর প্রশ্ন ব্যবহার করে LLM দিয়ে চূড়ান্ত উত্তর তৈরি করে। শুধু context থেকে উত্তর দেয়, hallucinate করে না।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Input** | `sql_query.optimized_context` | `str` | Structured database context |
| **Output** | `sql_query.final_answer` | `str` | LLM generated চূড়ান্ত উত্তর |

**পরবর্তী Node:** → `sql_query_support_check`

---

### Node 11: `sql_query_support_check`
**ফাইল:** `nodes/sql_query_support_check.py` | **Function:** `sql_query_support_check_node`

**কাজের বিবরণ:**
LLM generated উত্তর সত্যিই database context দ্বারা supported কিনা যাচাই করে। Retry mechanism সহ (max 3 বার)।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `sql_query.final_answer` | `str` | যাচাইয়ের জন্য উত্তর |
| **Input** | `sql_query.optimized_context` | `str` | Context যার বিপরীতে যাচাই হবে |
| **Input** | `sql_query.retry_count` | `int` | কতবার retry হয়েছে |
| **Output** | `sql_query.answer_status` | `str` | `"found"` বা `"not_found"` |
| **Output** | `sql_query.retry_count` | `int` | Updated retry count |

**পরবর্তী Node:** → `END`

---

## Phase 3 — SQL Retrieve Path (৫টি Node)

> **উদ্দেশ্য:** Embedding + BM25 hybrid search ব্যবহার করে PostgreSQL documents table থেকে semantic তথ্য retrieve করে।

---

### Node 12: `sql_retrieve_check`
**ফাইল:** `nodes/sql_retrieve_check.py` | **Function:** `sql_retrieve_check_node`

**কাজের বিবরণ:**
Semantic search-এর জন্য query উপযুক্ত কিনা এবং যথেষ্ট তথ্য আছে কিনা যাচাই করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Output** | `sql_retrieve.need_more_info` | `bool` | `True` = আরো তথ্য দরকার |
| **Output** | `sql_retrieve.final_answer` | `str` | Clarification message (need_more_info এ) |

**Routing:**
- `need_more_info=True` → `sql_query_short_info_response`
- অন্যথায় → `sql_retrieve_create`

---

### Node 13: `sql_retrieve_create`
**ফাইল:** `nodes/sql_retrieve_create.py` | **Function:** `sql_retrieve_create_node`

**কাজের বিবরণ:**
User এর প্রশ্ন থেকে semantic search এর জন্য keyword-rich search query তৈরি করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Output** | `sql_retrieve.search_query` | `str` | Semantic search এর জন্য optimized keywords |

**পরবর্তী Node:** → `sql_retrieve_context`

---

### Node 14: `sql_retrieve_context`
**ফাইল:** `nodes/sql_retrieve_context.py` | **Function:** `sql_retrieve_context_node`

**কাজের বিবরণ:**
Embedding + BM25 hybrid search (RRF score) ব্যবহার করে PostgreSQL documents table থেকে সবচেয়ে প্রাসঙ্গিক documents খোঁজে। Date, author, priority, score সহ annotated format তৈরি করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `sql_retrieve.search_query` | `str` | Search keywords |
| **Output** | `sql_retrieve.raw_context` | `str` | Plain content text |
| **Output** | `sql_retrieve.context_with_meta` | `str` | Date/author/priority সহ formatted context |
| **Output** | `sql_retrieve.context_found` | `bool` | কোনো result পাওয়া গেছে কিনা |

**পরবর্তী Node:** → `sub_query_router_node`

---

### Node 15: `sql_retrieve_response`
**ফাইল:** `nodes/sql_retrieve_response.py` | **Function:** `sql_retrieve_response_node`

**কাজের বিবরণ:**
Retrieved context এবং user এর প্রশ্ন ব্যবহার করে LLM দিয়ে চূড়ান্ত উত্তর তৈরি করে। Academic tone বজায় রাখে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Input** | `sql_retrieve.context_with_meta` | `str` | Annotated retrieved context |
| **Output** | `sql_retrieve.final_answer` | `str` | LLM generated উত্তর |

**পরবর্তী Node:** → `sql_retrieve_support_check`

---

### Node 16: `sql_retrieve_support_check`
**ফাইল:** `nodes/sql_retrieve_support_check.py` | **Function:** `sql_retrieve_support_check_node`

**কাজের বিবরণ:**
উত্তরটি context দ্বারা supported কিনা যাচাই করে। তিনটি verdict: `yes`, `no_support`, `hallucination`। Hallucination হলে retry, no_support হলে সরাসরি `no_answer_found`।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Input** | `sql_retrieve.final_answer` | `str` | যাচাইয়ের উত্তর |
| **Input** | `sql_retrieve.context_with_meta` | `str` | Source context |
| **Input** | `sql_retrieve.retry_count` | `int` | এখন পর্যন্ত retry count |
| **Output** | `sql_retrieve.supported` | `bool` | উত্তর গ্রহণযোগ্য কিনা |
| **Output** | `sql_retrieve.retry_count` | `int` | Updated retry count |

**Routing:**
- `supported=True` → `END`
- `supported=False` + `retry_count < MAX_RETRIES` → `sql_retrieve_response` (retry)
- `no_support` বা `retry_count >= MAX_RETRIES` → `no_answer_found`

---

## Phase 4 — Web Search Path (৪টি Node)

> **উদ্দেশ্য:** DuckDuckGo দিয়ে ইন্টারনেট search করে বাইরের তথ্য আনে।

---

### Node 17: `web_search_rewrite`
**ফাইল:** `nodes/web_search_rewrite.py` | **Function:** `web_search_rewrite_node`

**কাজের বিবরণ:**
Phase 1 এর rewritten query-কে web search engine এর জন্য optimized English keyword query-তে রূপান্তর করে (3-10 words)। Top-level `rewritten_query` পরিবর্তন করে না।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `rewritten_query` | `str` | Phase 1 output |
| **Output** | `web_search.rewritten_query` | `str` | Web search এর জন্য optimized English query |

**পরবর্তী Node:** → `web_search_docs`

---

### Node 18: `web_search_docs`
**ফাইল:** `nodes/web_search_docs.py` | **Function:** `web_search_docs_node`

**কাজের বিবরণ:**
DuckDuckGo (DDGS) দিয়ে top-5 web result search করে। প্রতিটি result এর title, URL, snippet (max 800 chars) সংগ্রহ করে formatted context তৈরি করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `web_search.rewritten_query` | `str` | Web search query |
| **Output** | `web_search.context` | `str` | Title + URL + Snippet সহ formatted web results |

**পরবর্তী Node:** → `sub_query_router_node`

---

### Node 19: `web_search_response`
**ফাইল:** `nodes/web_search_response.py` | **Function:** `web_search_response_node`

**কাজের বিবরণ:**
Web search results এবং user এর original প্রশ্ন ব্যবহার করে LLM দিয়ে চূড়ান্ত উত্তর তৈরি করে। User এর ভাষায় (বাংলা/ইংরেজি) উত্তর দেয়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন (rewritten নয়) |
| **Input** | `web_search.context` | `str` | Web search results |
| **Output** | `web_search.final_answer` | `str` | LLM generated উত্তর |

**পরবর্তী Node:** → `web_search_support_check`

---

### Node 20: `web_search_support_check`
**ফাইল:** `nodes/web_search_support_check.py` | **Function:** `web_search_support_check_node`

**কাজের বিবরণ:**
Web search উত্তর web context দ্বারা supported কিনা যাচাই করে। Phase 3 এর মতোই `yes` / `no_support` / `hallucination` verdict।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Input** | `web_search.final_answer` | `str` | যাচাইয়ের উত্তর |
| **Input** | `web_search.context` | `str` | Source context |
| **Input** | `web_search.retry_count` | `int` | Retry count |
| **Output** | `web_search.final_answer` | `str` | Updated (success বা cleared) |
| **Output** | `web_search.retry_count` | `int` | Updated retry count |
| **Output** | `answer_status` | `str` | `"found"` বা `"not_found"` |
| **Output** | `final_answer` | `str` | Top-level (success এ) |

**Routing:**
- `answer_status="found"` → `END`
- `retry_count < MAX_RETRIES` → `web_search_response` (retry)
- `retry_count >= MAX_RETRIES` → `no_answer_found`

---

## Phase 5 — Hybrid Sub-Query Path (৭টি Node)

> **উদ্দেশ্য:** জটিল multi-intent প্রশ্নকে ছোট sub-questions-এ ভেঙে parallel-এ সব path চালিয়ে answers merge করে।

---

### Node 21: `hybrid_depth_check`
**ফাইল:** `nodes/hybrid_depth_check.py` | **Function:** `hybrid_depth_check_node`

**কাজের বিবরণ:**
Recursive hybrid execution রোধ করার guard node। Sub-query থেকে আবার hybrid call হতে পারবে না (MAX_HYBRID_DEPTH = 1)। Depth increment করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `hybrid.depth` | `int` | বর্তমান recursion depth (শুরুতে 0) |
| **Output** | `hybrid.depth` | `int` | Depth + 1 |

**Routing:**
- `depth <= MAX_HYBRID_DEPTH (1)` → `create_sub_questions`
- `depth > 1` → `sql_retrieve_check` (fallback, recursion রোধ)

---

### Node 22: `create_sub_questions`
**ফাইল:** `nodes/hybrid_create_sub_questions.py` | **Function:** `create_sub_questions_node`

**কাজের বিবরণ:**
Complex প্রশ্নকে ২-৪টি self-contained, independent sub-questions-এ decompose করে। প্রতিটি sub-question আলাদাভাবে উত্তর দেওয়া যাবে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `rewritten_query` | `str` | Phase 1 output |
| **Output** | `hybrid.total_sub_q` | `int` | মোট sub-question সংখ্যা |
| **Output** | `hybrid.sub_query_list` | `list[str]` | Sub-questions এর list |

**পরবর্তী:** → `dispatch_sub_queries_node` (conditional edge, Send API)

---

### Node 23: `dispatch_sub_queries` *(Conditional Edge)*
**ফাইল:** `nodes/hybrid_dispatch_sub_queries.py` | **Function:** `dispatch_sub_queries_node`

**কাজের বিবরণ:**
LangGraph এর Send API ব্যবহার করে প্রতিটি sub-question-কে আলাদা parallel branch হিসেবে `rewrite_query` node থেকে শুরু করায়। প্রতিটি branch সম্পূর্ণ independent।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `hybrid.sub_query_list` | `list[str]` | Dispatch করার sub-questions |
| **Input** | `hybrid.depth` | `int` | Depth (sub-state-এ পাস করা হয়) |
| **Output** | `List[Send]` | — | Per sub-question এর জন্য একটি Send object |

**প্রতিটি Send করা sub-state-এ:**
```
is_sub_query_call = True
user_input = <sub_question>
hybrid.depth = <current_depth>
```

---

### Node 24: `append_sub_answer`
**ফাইল:** `nodes/hybrid_append_sub_answer.py` | **Function:** `append_sub_answer_node`

**কাজের বিবরণ:**
Parallel sub-query branch শেষ হলে fan-in convergence point। প্রতিটি branch এর উত্তর `hybrid.sub_query_ans` list-এ append করে (`operator.add` reducer)।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `parent_sub_query` | `str` | Sub-question text |
| **Input** | `final_answer` | `str` | Branch এর top-level উত্তর |
| **Input** | `decided_path` | `str` | কোন path উত্তর দিয়েছে |
| **Output** | `hybrid.sub_query_ans` | `list` | Appended SubQueryAnswer record |
| **Output** | `hybrid.sub_ans_count` | `int` | +1 increment |

**পরবর্তী Node:** → `merge_sub_answers`

---

### Node 25: `merge_sub_answers`
**ফাইল:** `nodes/hybrid_merge_sub_answers.py` | **Function:** `merge_sub_answers_node`

**কাজের বিবরণ:**
সব sub-query এর collected answers গুলোকে LLM দিয়ে একটি unified, coherent final response-এ merge করে। Redundancy eliminate করে, সব important facts সংরক্ষণ করে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `hybrid.sub_query_ans` | `list[SubQueryAnswer]` | সব sub-answers |
| **Input** | `user_input` | `str` | Original complex প্রশ্ন |
| **Output** | `final_answer` | `str` | Top-level merged উত্তর |
| **Output** | `answer_status` | `str` | `"pending"` (support check এর জন্য) |

**পরবর্তী Node:** → `merge_support_check`

---

### Node 26: `merge_support_check`
**ফাইল:** `nodes/hybrid_merge_support_check.py` | **Function:** `merge_support_check_node`

**কাজের বিবরণ:**
Merged final answer সত্যিই sub-answer contexts দ্বারা supported কিনা যাচাই করে। Hallucination বা contradictions ধরে।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `final_answer` | `str` | Merged উত্তর |
| **Input** | `hybrid.sub_query_ans` | `list` | Evidence contexts |
| **Input** | `hybrid.merge_retries` | `int` | Retry count |
| **Output** | `answer_status` | `str` | `"found"` বা `"not_found"` |
| **Output** | `hybrid.merge_retries` | `int` | Updated retry count |

**পরবর্তী Node:** → `merge_retry_check`

---

### Node 27: `merge_retry_check`
**ফাইল:** `nodes/hybrid_merge_retry_check.py` | **Function:** `merge_retry_check_node`

**কাজের বিবরণ:**
Hybrid path এর final gate node। Answer accepted হলে END, নতুবা retry অথবা exhaustion message দেয়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `answer_status` | `str` | `"found"` বা `"not_found"` |
| **Input** | `hybrid.merge_retries` | `int` | Current retry count |
| **Output** | `final_answer` | `str` | Final (success) বা exhaustion message |
| **Output** | `answer_status` | `str` | Finalized status |

**Routing:**
- `answer_status="found"` → `END`
- `merge_retries < MAX_RETRIES` → `merge_sub_answers` (retry)
- `merge_retries >= MAX_RETRIES` → `no_answer_found`

---

## Utility Nodes (সব Path-এ ব্যবহৃত)

---

### Node 28: `sub_query_router_node`
**ফাইল:** `nodes/graph.py` (inline) | **Function:** `sub_query_router_node`

**কাজের বিবরণ:**
Central gateway node। Context collection এর পর সব path-এর জন্য routing decision নেয়। Is_sub_query_call চেক করে hybrid branch গুলো `append_sub_answer`-এ পাঠায়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `is_sub_query_call` | `bool` | Sub-query branch কিনা |
| **Input** | `decided_path` | `str` | রুটিং এর পথ |
| **Output** | *(state unchanged)* | — | Pass-through, শুধু routing |

**Routing Decisions:**
| Condition | পরবর্তী Node |
|-----------|-------------|
| `is_sub_query_call=True` | `append_sub_answer` |
| `sql_query` + `row_count > 0` | `sql_query_response` |
| `sql_query` + `row_count = 0` | `fallback_dispatcher` |
| `sql_retrieve` + `context_found=True` | `sql_retrieve_response` |
| `sql_retrieve` + `context_found=False` | `no_answer_found` |
| `web_search` + context আছে | `web_search_response` |
| `web_search` + context নেই | `no_answer_found` |

---

### Node 29: `no_answer_found`
**ফাইল:** `nodes/no_answer_found.py` | **Function:** `no_answer_found_node`

**কাজের বিবরণ:**
সব retry exhausted হলে বা তথ্য পাওয়া না গেলে LLM দিয়ে polite apology message তৈরি করে। User এর ভাষায় (বাংলা/ইংরেজি) উত্তর দেয়।

| | Field | Type | বিবরণ |
|--|-------|------|--------|
| **Input** | `user_input` | `str` | মূল প্রশ্ন |
| **Output** | `final_answer` | `str` | User-friendly apology message |

**পরবর্তী Node:** → `END`

---

## সম্পূর্ণ Flow Diagram

```
START
  │
  ▼
rewrite_query          ← user_input → rewritten_query
  │
  ▼
llm_decide_path        ← rewritten_query → decided_path + confidence_score
  │
  ├── [confidence < 0.7] ──────────────────────────┐
  ├── [sql_query] →  sql_query_info_check           │
  ├── [sql_retrieve] → sql_retrieve_check           │
  ├── [web_search] → web_search_rewrite             │
  └── [hybrid] ──────────────────────────────────── ▼
                                          hybrid_depth_check
                                                   │
                                    ┌──────────────┴──────────────┐
                               [depth OK]                   [too deep]
                                   ▼                              ▼
                         create_sub_questions          sql_retrieve_check
                                   │
                              dispatch (Send API)
                         ┌─────────┴──────────┐
                    [sub_q1]              [sub_q2]  ... parallel
                    rewrite_query         rewrite_query
                         │                    │
                    [full pipeline]      [full pipeline]
                         └──────┬────────────┘
                                ▼
                        append_sub_answer
                                │
                        merge_sub_answers
                                │
                       merge_support_check
                                │
                        merge_retry_check
                                │
                    ┌───────────┴───────────┐
                 [found]              [not_found]
                   END              no_answer_found → END

─── SQL Query Path ───
sql_query_info_check
    ├── [short_info/not_possible] → sql_query_short_info_response → sub_query_router_node
    └── [ok] → sql_query_create → sql_query_db_call → sql_query_row_check
                                                            │
                     ┌──────────────────────────────────────┤
                [row=0]                [row=1]          [row>1]
                   ▼                     ▼                  ▼
         fallback_dispatcher   sub_query_router_node  sql_query_optimize
                │                                          │
        sql_retrieve_check                        sub_query_router_node
                                                           │
                                              sql_query_response → sql_query_support_check → END

─── SQL Retrieve Path ───
sql_retrieve_check
    ├── [need_more_info] → sql_query_short_info_response → sub_query_router_node
    └── [ok] → sql_retrieve_create → sql_retrieve_context → sub_query_router_node
                                                                      │
                                                           sql_retrieve_response
                                                                      │
                                                          sql_retrieve_support_check
                                                                      │
                                              ┌─────────────────────┬┤
                                           [ok]              [retry] │[no_support]
                                           END          sql_retrieve  no_answer_found
                                                          _response       │
                                                                        END

─── Web Search Path ───
web_search_rewrite → web_search_docs → sub_query_router_node
                                                │
                                     web_search_response
                                                │
                                   web_search_support_check
                                                │
                             ┌──────────────────┴──────────────────┐
                          [ok]                [retry]           [no_support]
                          END          web_search_response    no_answer_found
                                                                    │
                                                                   END
```

---

## State Schema সারসংক্ষেপ

### Top-Level State Fields
| Field | Type | কোথায় Set হয় | কাজ |
|-------|------|--------------|-----|
| `user_input` | `str` | শুরুতে | মূল প্রশ্ন |
| `rewritten_query` | `str` | `rewrite_query` | LLM rewrite করা প্রশ্ন |
| `decided_path` | `str` | `llm_decide_path` | নির্বাচিত path |
| `confidence_score` | `float` | `llm_decide_path` | Router এর confidence |
| `final_answer` | `str` | সব terminal node | চূড়ান্ত উত্তর |
| `answer_status` | `str` | support_check nodes | `"found"` / `"not_found"` |
| `is_sub_query_call` | `bool` | `dispatch_sub_queries` | Sub-query branch flag |
| `parent_sub_query` | `str` | `dispatch_sub_queries` | মূল sub-question |

### Nested State Fields
| Nested State | প্রধান Fields |
|-------------|-------------|
| `sql_query` | `query_str`, `row_count`, `raw_context`, `optimized_context`, `final_answer`, `retry_count`, `short_info`, `not_possible`, `answer_status` |
| `sql_retrieve` | `search_query`, `raw_context`, `context_with_meta`, `context_found`, `final_answer`, `retry_count`, `need_more_info`, `supported` |
| `web_search` | `rewritten_query`, `context`, `final_answer`, `retry_count` |
| `hybrid` | `depth`, `total_sub_q`, `sub_query_list`, `sub_query_ans`, `sub_ans_count`, `merge_retries` |

---

## Constants
| Constant | Value | কাজ |
|----------|-------|-----|
| `MAX_RETRIES` | `3` | Maximum retry সংখ্যা |
| `MAX_HYBRID_DEPTH` | `1` | Hybrid recursion এর সর্বোচ্চ depth |
| `_MAX_RESULTS` | `5` | DuckDuckGo এর max results |
| `_MAX_SUB_QUESTIONS` | `4` | Hybrid এর max sub-questions |
