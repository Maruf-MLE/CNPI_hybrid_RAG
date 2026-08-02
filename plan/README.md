# CNPI RAG System

## Project Goal

CNPI RAG System-এর লক্ষ্য হলো College সম্পর্কিত তথ্য, Notice, Department Information, Teacher Information, Student Services এবং অন্যান্য Structured ও Unstructured Data থেকে সঠিক, দ্রুত এবং Context-Aware উত্তর প্রদান করা।

সিস্টেমটি Query-এর ধরন অনুযায়ী স্বয়ংক্রিয়ভাবে সঠিক Retrieval Path নির্বাচন করবে এবং প্রয়োজনে Query-কে Sub Query-তে বিভক্ত করে Parallel Processing-এর মাধ্যমে উত্তর তৈরি করবে।

### Supported Retrieval Methods

* SQL Query Path → Structured Database Retrieval
* SQL Retrieve Path → Semantic Retrieval
* Web Search Path → External Information Retrieval
* Hybrid Processing → Complex / Multi-Step Questions
* Sub Query Processing → Parallel Question Decomposition

### Design Objectives

* High Accuracy
* Low Latency
* Minimal Hallucination
* Context Supported Answers
* Modular Architecture
* Scalable Node Design
* Production Ready State Management
* Easy Future Extension

---

# High Level Architecture

```text
User Input
    ↓
Rewrite Query
    ↓
LLM Decide Path
    ↓

Selected Path
    ├── SQL Query Path
    ├── SQL Retrieve Path
    └── Web Search Path

    ↓
Context Ready
    ↓
Sub Query Check

        ├── Yes
        │       ↓
        │ Append Sub Answer
        │       ↓
        │ Merge Answers
        │
        └── No
                ↓
            Generate Response

    ↓
Support Validation
    ↓
Final Response
```

---

# Path Selection Logic

LLM Router Query Analysis করে Retrieval Path নির্বাচন করবে।

Possible Outputs:

```text
path:
    - sql_query
    - sql_retrieve
    - hybrid path
    - web_search

confidence_score
```

### Routing Strategy

```text
High Confidence
    ↓
Direct Path Execution

Low Confidence
    ↓
Hybrid / Multi-Step Processing
```

---

# SQL Query Path

Structured Data থেকে নির্ভুল উত্তর পাওয়ার জন্য ব্যবহার হবে।

### Flow

```text
SQL Query Path
    ↓
Query Type Check
    ↓
Metadata Search Query Creation
    ↓
SQL Query Generation
    ↓
Database Execution
    ↓
Row Validation
    ↓
Context Optimization
    ↓
LLM Response
    ↓
Support Validation
    ↓
Sub Query Check
    ↓
Final Response
```

### Fallback

```text
Row = 0
    ↓
SQL Retrieve Path
```

###

---

# SQL Retrieve Path

Semantic Retrieval প্রয়োজন হলে ব্যবহার হবে।

### Retrieval Stack

```text
Metadata Search
    ↓
Embedding Search
    ↓
BM25 Search
    ↓
Context Ranking
    ↓
Optimized Context
```

### Flow

```text
Query Analysis
    ↓
Retrieve Query Creation
    ↓
Embedding + BM25 Retrieval
    ↓
Context Generation
    ↓
LLM Response
    ↓
Support Validation
    ↓
Sub Query Check
    ↓
Final Response
```

###

---

# Web Search Path

Local Knowledge Base-এ উত্তর না থাকলে External Information Retrieval করা হবে।

### Flow

```text
Rewrite Query
    ↓
Web Search
    ↓
Document Collection
    ↓
Context Extraction
    ↓
LLM Response
    ↓
Support Validation
    ↓
Sub Query Check
    ↓
Final Response
```

###

---

````text
# Hybrid Path

Hybrid Path ব্যবহার হবে যখন Router বুঝবে যে একটি Query-এর উত্তর একটি Retrieval Source থেকে পাওয়া সম্ভব নয় অথবা Query-টি Multiple Intent / Multiple Information Source প্রয়োজন।

উদাহরণ:

```text
Who is the head of CSE department and
what notices were published this week?
```

এখানে:

* Department Head → SQL Query Path
* Recent Notices → SQL Retrieve Path

অর্থাৎ একটি Path যথেষ্ট নয়।

---

## Hybrid Path Flow

```text
Original Query
    ↓
Depth Check
    ↓
Create Sub Queries
    ↓
Dispatch Sub Queries
    ↓

Sub Query 1 ─────► Router ─────► SQL Query Path
Sub Query 2 ─────► Router ─────► SQL Retrieve Path
Sub Query 3 ─────► Router ─────► Web Search Path

                    (Parallel)

    ↓
Append Sub Answers
    ↓
All Sub Answers Completed?
    ↓
Merge Answers
    ↓
Generate Final Response
    ↓
Support Validation
    ↓
Final Response
```

---

## Hybrid Path Responsibilities

### 1. Query Decomposition

Complex Query-কে ছোট ছোট Independent Query-তে ভাগ করা।

Example:

```text
Original Query

Who is the head of CSE department and
what notices were published this week?
```

↓

```text
Sub Query 1:
Who is the head of CSE department?

Sub Query 2:
What notices were published this week?
```

---

### 2. Parallel Execution

প্রতিটি Sub Query আলাদা State Branch-এ Execute হবে।

```text
Sub Query 1 → SQL Query Path

Sub Query 2 → SQL Retrieve Path
```

সব Sub Query একসাথে চলবে।

---

### 3. Answer Collection

প্রতিটি Sub Query শেষ হলে:

```text
sub_answer
```

global merge state-এ append হবে।

```text
append_sub_answer()
```

---

### 4. Answer Merge

সব Sub Query Complete হলে:

```text
all_sub_answers_ready == True
```

↓

```text
merge_sub_answers()
```

↓

একটি Unified Response তৈরি হবে।

---

### 5. Final Validation

Merged Answer-এর উপর আবার Support Check চলবে।

```text
Merged Answer
      ↓
Support Validation
      ↓
Final Response
```

---

## Hybrid Path Rules

* Maximum Depth Control
* Maximum Sub Query Limit
* State Isolation
* Parallel Execution
* Merge Retry Control
* Context Preservation
* Duplicate Removal
* Final Support Validation

---

## Hybrid Path Nodes

```text
hybrid_depth_check

create_sub_queries

dispatch_sub_queries

append_sub_answer

all_sub_answers_ready

merge_sub_answers

merge_support_check

merge_retry_check
```


````

---

# Answer Merge System

Sub Query Result Return হওয়ার পর সরাসরি User-কে Response দেওয়া হবে না।

প্রথমে Merge Layer-এ পাঠানো হবে।

### Flow

```text
Sub Answer
    ↓
Append To State
    ↓
All Sub Answers Ready?
    ↓
Merge Answers
    ↓
Final Response
```

### Responsibilities

* Answer Aggregation
* Duplicate Removal
* Context Preservation
* Formatting
* Final Validation

---

# Retry Strategy

Hallucination এবং Unsupported Answer কমানোর জন্য প্রতিটি Path-এ Retry System থাকবে।

### Retry Limits

```text
sql_query_retry_count      <= 3

sql_retrieve_retry_count   <= 3

web_search_retry_count     <= 3

merge_retry_count          <= 3
```

### Validation Flow

```text
Generated Answer
    ↓
Support Check
    ↓

Supported?
    ├── Yes → Continue
    └── No  → Retry
```

---

# Implementation Roadmap

## Phase 1

Foundation + Routing

Nodes:

* rewrite_query
* llm_decide_path

---

## Phase 2

SQL Query Path

Nodes:

* sql_query_info_check
* sql_query_create
* sql_query_db_call
* sql_query_row_check
* sql_query_context_optimizer
* sql_query_response
* sql_query_support_check

---

## Phase 3

SQL Retrieve Path

Nodes:

* sql_retrieve_check
* sql_retrieve_create
* sql_retrieve_context
* sql_retrieve_response
* sql_retrieve_support_check

---

## Phase 4

Web Search Path

Nodes:

* web_search_rewrite
* web_search_docs
* web_search_response
* web_search_support_check

---

## Phase 5

Sub Query System

Nodes:

* create_sub_queries
* dispatch_sub_queries
* append_sub_answer
* merge_sub_answers
* merge_support_check
* merge_retry_check

---

# Development Rules

1. state.py হলো State-এর Single Source of Truth।
2. Architecture Diagram হলো Flow-এর Single Source of Truth।
3. কোনো Flow অনুমান করে পরিবর্তন করা যাবে না।
4. কোনো State Field অনুমান করে যোগ করা যাবে না।
5. Diagram এবং State-এর মধ্যে Conflict পাওয়া গেলে Clarification নিতে হবে।
6. Low Latency এবং High Accuracy সর্বোচ্চ অগ্রাধিকার।
7. Context Supported Answer বাধ্যতামূলক।
8. Unsupported Answer সর্বোচ্চ 3 বার Retry করা যাবে।
9. Sub Query Execution অবশ্যই State Isolated হতে হবে।
10. Merge Layer bypass করা যাবে না।
11. Final Response-এর আগে Support Validation বাধ্যতামূলক।
12. Node Contract এবং State Contract কঠোরভাবে অনুসরণ করতে হবে।





Tect stack

| আইটেম | ব্যবহার |
| --- | --- |
| 🔹 Python  | প্রোগ্রামিং ভাষা |
| 🔹 LangGraph | Flow control, routing |
| 🔹 LangChain | LLM wrapper |
| 🔹 Groq ai | llm
| 🔹 PostgreSQL | ডেটাবেস |
| 🔹 sentence-transformers | Embedding model |
| 🔹 BM25 search (pymorphy2, scikit-learn) | কন্টেন্ট সার্চ |
| 🔹 SERP API / DuckDuckGo | Web search |



2️⃣  Project Structure
    cnpi_rag/
    ├── state.py         
    ├── nodes/
    │   ├── __init__.py
    │   ├── entry.py         ← Phase 1
    │   ├── sql_query.py     ← Phase 2
    │   ├── sql_retrieve.py  ← Phase 3
    │   ├── web_search.py    ← Phase 4
    │   └── hybrid.py        ← Phase 5
    ├── graph.py             ← LangGraph building
    ├── utils/
    │   ├── llm_utils.py     ← LLM wrapper
    │   ├── db_utils.py      ← DB connection
    │   └── search_utils.py  ← BM25 + embedding
    └── prompts/
        └── *.json           ← সব LLM prompt



sob jaigai system chat prompt  template,chain  egula thakbe TypedDict use hobe state e 

