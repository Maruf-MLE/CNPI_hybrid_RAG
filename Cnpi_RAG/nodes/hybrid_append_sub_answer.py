"""
Append Sub Answer Node - Phase 5
====================================

Fan-in convergence point: called once per completed sub-query branch.

Each parallel sub-query branch (dispatched by `dispatch_sub_queries`) converges
here after completing its own path (SQL Query / SQL Retrieve / Web Search).
This node reads the sub-query's result from state and appends a SubQueryAnswer
record to hybrid.sub_query_ans using the operator.add reducer defined in state.py.

Key design:
- The operator.add reducer on hybrid.sub_query_ans means LangGraph APPENDS each
  branch's partial result to the shared list, rather than overwriting it.
- sub_ans_count is incremented; graph.py checks sub_ans_count == total_sub_q
  to decide when to proceed to merge_sub_answers.

State read:
    state.user_input          → the sub-question text for this branch
    state.final_answer        → the answer this branch produced (top-level)
    state.decided_path        → which path answered (source_path)
    state.sql_query / sql_retrieve / web_search  → for context extraction

State written:
    hybrid.sub_query_ans   → appended (via reducer) with one SubQueryAnswer
    hybrid.sub_ans_count   → incremented by 1

References:
    plan/state.py → SubQueryAnswer, HybridPathState.sub_query_ans (operator.add)
    plan/README.md → "Answer Collection" section
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState, SubQueryAnswer, PathName


def _extract_context_from_state(state: RAGState, source_path: PathName) -> Optional[str]:
    """Pull the supporting context from whichever path answered this sub-query."""
    if source_path == "sql_query":
        return state.get("sql_query", {}).get("optimized_context") or \
               state.get("sql_query", {}).get("raw_context")
    elif source_path == "sql_retrieve":
        return state.get("sql_retrieve", {}).get("context_with_meta") or \
               state.get("sql_retrieve", {}).get("raw_context")
    elif source_path == "web_search":
        return state.get("web_search", {}).get("context")
    return None


def _extract_clarification_from_state(state: RAGState, source_path: PathName) -> Optional[str]:
    """Extract clarification message if the sub-query hit a need_more_info / short_info state."""
    if source_path == "sql_query":
        sql_state = state.get("sql_query", {})
        if sql_state.get("short_info") or sql_state.get("not_possible"):
            return sql_state.get("final_answer") or sql_state.get("clarification")
    elif source_path == "sql_retrieve":
        sql_retrieve_state = state.get("sql_retrieve", {})
        if sql_retrieve_state.get("need_more_info"):
            return sql_retrieve_state.get("final_answer") or sql_retrieve_state.get("clarification")
    elif source_path == "web_search":
        # Web search typically doesn't have need_more_info, but check answer_status
        if state.get("answer_status") == "need_more_info":
            return state.get("final_answer")
    return None


def append_sub_answer_node(state: RAGState) -> Dict[str, Any]:
    """Collect one completed sub-query answer into the hybrid accumulator.

    Input  : top-level state fields set by the completing sub-query branch
    Output : hybrid.sub_query_ans  (appended, reducer handles fan-in)
             hybrid.sub_ans_count  (incremented)
    """
    hybrid_state = state.get("hybrid", {})
    sub_ans_count: int = hybrid_state.get("sub_ans_count", 0)

    # The sub-question and answer live at the TOP LEVEL of the branch state
    sub_question: str = state.get("parent_sub_query") or state.get("user_input", "")
    final_answer: str = state.get("final_answer", "").strip()
    source_path: PathName = state.get("decided_path", "sql_retrieve")
    answer_status: str = state.get("answer_status", "pending")

    # Check if this sub-query hit a "need_more_info" / "short_info" state
    clarification: Optional[str] = _extract_clarification_from_state(state, source_path)
    
    # Extract supporting context for transparency
    context: Optional[str] = _extract_context_from_state(state, source_path)

    # Priority 1: If there's a clarification message (need_more_info / short_info),
    # use that as the final_answer so merge node knows this sub-query needs more info
    if clarification:
        final_answer = clarification
        context = None  # No context available when clarification is needed
        print(
            f"[append_sub_answer] Sub-query #{sub_ans_count + 1} needs clarification: "
            f"'{sub_question[:60]}'"
        )
    # Priority 2: If no answer was produced (e.g. skipped response node),
    # use the context as the answer for the merge node to synthesize
    elif not final_answer and context:
        final_answer = context
    # Priority 3: Ultimate fallback if still no answer/context
    elif not final_answer:
        final_answer = "দুঃখিত, এই প্রশ্নের উত্তর পাওয়া যায়নি।"

    record: SubQueryAnswer = {
        "query": sub_question,
        "context": context,
        "final_answer": final_answer,
        "source_path": source_path,
    }

    new_count = sub_ans_count + 1

    print(
        f"[append_sub_answer] Collected sub-answer #{new_count}: "
        f"'{sub_question[:60]}' via {source_path}"
    )

    return {
        "hybrid": {
            **hybrid_state,
            # operator.add on sub_query_ans means this list is APPENDED, not replaced
            "sub_query_ans": [record],
            "sub_ans_count": new_count,
        }
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে?",
        "parent_sub_query": "CSE বিভাগের প্রধান কে?",
        "is_sub_query_call": True,
        "decided_path": "sql_query",
        "final_answer": "CSE বিভাগের প্রধান হলেন ড. মোহাম্মদ রহমান।",
        "answer_status": "found",
        "sql_query": {
            "optimized_context": "Name: Dr. Mohammad Rahman, Dept: CSE, Role: Head",
            "final_answer": "CSE বিভাগের প্রধান হলেন ড. মোহাম্মদ রহমান।",
            "retry_count": 0,
        },
        "hybrid": {
            "depth": 1,
            "total_sub_q": 2,
            "sub_query_list": [],
            "sub_query_ans": [],
            "sub_ans_count": 0,
            "merge_retries": 0,
        },
    }

    result = append_sub_answer_node(sample_state)
    print("\nAppended sub-answer:")
    for ans in result["hybrid"]["sub_query_ans"]:
        print(f"  query       : {ans['query']}")
        print(f"  final_answer: {ans['final_answer']}")
        print(f"  source_path : {ans['source_path']}")
    print(f"  sub_ans_count: {result['hybrid']['sub_ans_count']}")
