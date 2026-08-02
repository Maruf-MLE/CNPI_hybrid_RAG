"""
state.py

LangGraph State Schema for the College RAG System.
Stack: Django + LangChain / LangGraph + PostgreSQL

===============================================================================
CHANGELOG (this revision)
===============================================================================
- REMOVED: sql_clarification_message / sql_retrieve_clarification_message.
  These were redundant. When a path needs to ask the user for more info,
  it now just writes the question text into that path's own `final_answer`
  and sets top-level `answer_status = "need_more_info"`. Django's view reads
  answer_status to decide "is this a real answer or a clarifying question",
  so a separate string field added nothing except duplication.

- KEPT / CONFIRMED: `is_sub_query_call` and `parent_sub_query` at the TOP
  LEVEL of RAGState (not inside any per-path dict). Re-checked against the
  diagram: the diagram itself re-derives "am I a sub-query?" at the end of
  EVERY path (SQL Query, SQL Retrieve, Web Search) using a literal
  string-membership check -- "if user_query == s in sub_query_list". That
  is a real node in the diagram, repeated 3 times (once per path), and it
  is the ONLY mechanism the diagram defines for a path to know whether its
  answer should go back into the Hybrid merge step or straight to the user.

  We are NOT implementing that check as a literal string search against
  `hybrid.sub_query_list` at runtime, for two reasons:
    1. Under the nested-state design, SQLQueryPathState / SQLRetrievePathState
       / WebSearchPathState are not supposed to reach into `hybrid` -- doing
       so re-creates the exact coupling the nested design was meant to avoid.
    2. String-equality matching against a list of LLM-generated sub-questions
       is fragile (whitespace, punctuation, or a slightly reworded query all
       break the match silently).
  Instead, the Hybrid dispatch node sets `is_sub_query_call=True` and
  `parent_sub_query=<the exact sub-question text>` on the state BEFORE
  handing off to whichever path is chosen. Every path's terminal node then
  just reads that top-level flag instead of re-deriving it. This is a
  deliberate, disclosed deviation from the diagram's literal mechanism --
  functionally equivalent, structurally safer. Flagging this explicitly so
  it isn't mistaken for "matches the diagram exactly."

===============================================================================
KNOWN DIAGRAM GAPS (found on this re-check, not yet fixed in the diagram)
===============================================================================
1. SQL Query path's "Response user for need more info
   (sql_clarification_message)" box has ZERO outgoing edges in the diagram.
   Every other terminal-ish node (including SQL Retrieve's equivalent box)
   connects onward to the shared "if user_query == s in sub_query_list"
   check. This one is a dead end. The state/graph code below assumes it
   SHOULD connect onward like its SQL Retrieve counterpart -- please
   confirm and fix the .drawio file to match, or tell me if this was
   intentional.

2. SQL Query path's "row check" node, on the "Row = 1" branch, jumps
   straight to the shared sub-query-check node -- skipping the "LLM
   response" / "check response supported" nodes entirely. That means for
   the exactly-one-row case, `sql_query.final_answer` is never populated by
   an LLM call. Either that's intentional (single row = self-evidently the
   answer, format it directly without an LLM pass) or an edge is missing.
   This needs your confirmation before I encode it into a node.

3. SQL Query path's "row check", on "Row = 0", routes into SQL Retrieve
   path's "Create query: metadata search -> embed + BM25" node. This is a
   real cross-path handoff, not just a state-design detail -- SQL Query
   silently becomes SQL Retrieve mid-flight. Confirm this is intended; if
   so, the graph code needs an explicit edge from a sql_query node into a
   sql_retrieve node (not just "SQL Query path" and "SQL Retrieve path" as
   two independent entry points), which is a slightly different shape than
   "4 independent paths" the rest of the design assumes.

4. A handful of edges in the .drawio file point at unresolved/empty target
   cells (8 found) -- mostly around the Hybrid merge and "LLM decided Path"
   area. These look like leftover/disconnected arrows from editing rather
   than real logic, but worth a visual pass in draw.io to confirm nothing
   real got disconnected.

None of the above change the state SCHEMA below, except #1 and #3 will
matter once you write the actual graph edges -- flagging now so they don't
surprise you during node implementation.
===============================================================================

DESIGN DECISIONS CARRIED OVER FROM THE PREVIOUS REVISION
===============================================================================

1. NESTED STATE, NOT FLAT.
   Each of the 4 paths (Hybrid, SQL Query, SQL Retrieve, Web Search) has its
   OWN TypedDict. This is a deliberate fix for the bug found earlier in the
   diagram, where the Web Search path accidentally reused the SQL Query
   path's retry-counter name (`sql_path_issup`). With nested state, that
   kind of collision becomes structurally impossible.

   TRADE-OFF: when a node updates a nested field, it must return the WHOLE
   sub-dict for that path (e.g. the whole "sql_query" dict), not just the
   one key that changed -- LangGraph's default reducer replaces the value
   at a top-level key, it does not deep-merge nested dicts. Helper
   functions at the bottom of this file exist to make this safe.

2. confidence_score IS A FLOAT, NOT AN INT.
   The diagram said "confident_score: int" but then compared it against 0.7
   ("confident_Score > 0.7"). Fixed to float, range 0.0-1.0.

3. PathName and AnswerStatus are Literal types, not raw strings, so
   mypy/pyright catch typos like "sql_retrive" before they become runtime
   bugs.

4. Every retry counter defaults to 0 and lives ONLY inside this per-request
   state object. LangGraph builds a fresh state per `.invoke()`, so as long
   as this whole object is never persisted and reloaded for a *different*
   user question, retry counters can't leak across requests. Only persist
   `user_input` / `final_answer` / `answer_status` (and maybe
   `hybrid.sub_query_ans`, for logging) if you need history.

5. sub_query_ans uses an `operator.add` reducer, so parallel Hybrid
   sub-query branches (LangGraph Send API / map-reduce) concatenate their
   results instead of overwriting each other.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional, TypedDict, Any

from langchain_core.messages import BaseMessage


# ==============================================================================
# Shared enums / literal types
# ==============================================================================

PathName = Literal["hybrid", "sql_query", "sql_retrieve", "web_search"]

AnswerStatus = Literal["pending", "found", "not_found", "need_more_info"]


# ==============================================================================
# Config constants (NOT part of state -- these don't change per request)
# ==============================================================================

MAX_RETRIES: int = 3          # used by sql_query, sql_retrieve, web_search, merge
MAX_HYBRID_DEPTH: int = 1     # a sub-query is never allowed to choose "hybrid" again


# ==============================================================================
# Small record type used inside the Hybrid path
# ==============================================================================

class SubQueryAnswer(TypedDict):
    """One entry produced when a Hybrid sub-query finishes running through
    one of the OTHER three paths (sql_query / sql_retrieve / web_search)."""
    query: str
    context: Optional[str]      # None if no supporting context was found
    final_answer: str
    source_path: PathName       # which path actually answered this sub-query


# ==============================================================================
# Per-path state (nested inside the main RAGState)
# ==============================================================================

class HybridPathState(TypedDict, total=False):
    depth: int                                   # 0 = top-level request,
                                                   # 1 = already inside a
                                                   # sub-query dispatch.
    total_sub_q: int                              # number of sub-questions created
    sub_query_list: list[str]                     # the decomposed questions
    sub_query_ans: Annotated[list[SubQueryAnswer], operator.add]
    sub_ans_count: int                             # how many have been answered so far
    merge_retries: int                             # retries while merging sub-answers


class SQLQueryPathState(TypedDict, total=False):
    short_info: bool               # LLM said the user query lacks detail
    not_possible: bool             # LLM said this can't be answered via SQL at all
    missing_shift: bool            # True if shift is missing and required
    missing_department: bool       # True if department is missing and required
    missing_semester: bool         # True if semester is missing and required
    query_str: str                 # the generated SQL query text
    row_count: int                 # 0 / 1 / 1+  ("row check" in the diagram)
    raw_context: str               # rows returned straight from the DB call
    optimized_context: str         # rows re-ordered/annotated with priority + date
    contexts: list                 # list of retrieved context dicts
    context_found: bool            # whether any context was found
    formatted_context: str         # contexts formatted for the LLM
    search_query: str              # query used for retrieval
    retrieved_at: str              # timestamp of retrieval
    final_answer: str              # this path's own working answer / clarifying
                                    # question text (see AnswerStatus note below)
    retry_count: int
    generation_retry_count: int
    generation_error: bool


class SQLRetrievePathState(TypedDict, total=False):
    need_more_info: bool
    raw_context: str               # metadata search + embedding + BM25 result
    context_with_meta: str         # context annotated with date + priority
    context_found: bool            # False => diagram's "No and context=False" branch
    final_answer: str
    retry_count: int


class WebSearchPathState(TypedDict, total=False):
    rewritten_query: str           # query rewritten specifically for web search
    context: str                   # "Ready docs context" from the diagram
    final_answer: str
    retry_count: int


# ==============================================================================
# MAIN GRAPH STATE
# ==============================================================================

def merge_hybrid_path_state(old: dict, new: dict) -> dict:
    """Deep merge reducer for the hybrid nested state.
    Required because LangGraph parallel branches (Send API) emit multiple updates 
    for the top-level 'hybrid' key simultaneously. This reducer ensures lists are appended.
    """
    if not old: return new
    if not new: return old
    merged = {**old, **new}
    if "sub_query_ans" in old and "sub_query_ans" in new:
        merged["sub_query_ans"] = old["sub_query_ans"] + new["sub_query_ans"]
    return merged

def merge_dict_state(old: dict, new: dict) -> dict:
    if not old: return new
    if not new: return old
    return {**old, **new}

def replace_reducer(old: Any, new: Any) -> Any:
    return new


class RAGState(TypedDict, total=False):
    # ---- Entry -----------------------------------------------------------
    user_input: Annotated[str, replace_reducer]
    normalized_query: Annotated[str, replace_reducer]
    rewritten_query: Annotated[str, replace_reducer]

    # ---- Router ------------------------------------------------------------
    decided_path: Annotated[PathName, replace_reducer]
    confidence_score: Annotated[float, replace_reducer]

    # ---- Sub-query context ----
    is_sub_query_call: Annotated[bool, replace_reducer]
    parent_sub_query: Annotated[Optional[str], replace_reducer]

    # ---- Per-path nested state -----------------------------------------------
    hybrid: Annotated[HybridPathState, merge_hybrid_path_state]
    sql_query: Annotated[SQLQueryPathState, merge_dict_state]
    sql_retrieve: Annotated[SQLRetrievePathState, merge_dict_state]
    web_search: Annotated[WebSearchPathState, merge_dict_state]

    # ---- Chat history (carried across turns) ---------------------------------
    messages: Annotated[list[BaseMessage], operator.add]

    # ---- Shared final output -------------------------------------------------
    final_answer: Annotated[str, replace_reducer]
    answer_status: Annotated[AnswerStatus, replace_reducer]


# ==============================================================================
# Helper factories -- ALWAYS build state through these, never hand-write a dict.
# ==============================================================================

def new_hybrid_state() -> HybridPathState:
    return HybridPathState(
        depth=0,
        total_sub_q=0,
        sub_query_list=[],
        sub_query_ans=[],
        sub_ans_count=0,
        merge_retries=0,
    )


def new_sql_query_state() -> SQLQueryPathState:
    return SQLQueryPathState(
        short_info=False,
        not_possible=False,
        query_str="",
        row_count=0,
        raw_context="",
        optimized_context="",
        contexts=[],
        context_found=False,
        formatted_context="",
        search_query="",
        retrieved_at="",
        final_answer="",
        retry_count=0,
        generation_retry_count=0,
        generation_error=False,
    )


def new_sql_retrieve_state() -> SQLRetrievePathState:
    return SQLRetrievePathState(
        need_more_info=False,
        raw_context="",
        context_with_meta="",
        context_found=False,
        final_answer="",
        retry_count=0,
    )


def new_web_search_state() -> WebSearchPathState:
    return WebSearchPathState(
        rewritten_query="",
        context="",
        final_answer="",
        retry_count=0,
    )


def new_rag_state(user_input: str, messages: list[BaseMessage] | None = None) -> RAGState:
    """Entry point: call this ONCE per incoming user question,
    e.g. inside your Django view before graph.invoke(...).

    Parameters:
        user_input: the raw user question for this turn.
        messages:   accumulated chat history from previous turns
                    (list of HumanMessage / AIMessage).  Pass [] or None
                    for the first turn; pass the growing history list
                    for subsequent turns so the LLM can see prior context.
    """
    from langchain_core.messages import HumanMessage
    history = list(messages) if messages else []
    history.append(HumanMessage(content=user_input))
    return RAGState(
        user_input=user_input,
        normalized_query="",
        rewritten_query="",
        decided_path="sql_retrieve",   # placeholder, router will overwrite
        confidence_score=0.0,
        is_sub_query_call=False,
        parent_sub_query=None,
        hybrid=new_hybrid_state(),
        sql_query=new_sql_query_state(),
        sql_retrieve=new_sql_retrieve_state(),
        web_search=new_web_search_state(),
        final_answer="",
        answer_status="pending",
        messages=history,
    )
