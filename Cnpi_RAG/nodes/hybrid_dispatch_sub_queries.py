"""
Hybrid Dispatch Sub Queries Node - Phase 5
============================================

Dispatch all sub-questions in PARALLEL using LangGraph's Send API.

Each sub-question becomes an independent graph execution starting from
`rewrite_query` (Phase 1 entry), with:
    - is_sub_query_call = True
    - parent_sub_query  = <the sub-question text>
    - user_input        = <the sub-question text>
    - hybrid.depth      = current depth (prevents recursive hybrid)

After each parallel branch finishes its full path (SQL Query / SQL Retrieve /
Web Search), it will converge at `append_sub_answer`.

Implementation pattern:
    The node returns a list of `Send` objects, one per sub-question.
    LangGraph executes them concurrently and fans back into `append_sub_answer`.

State read:
    hybrid.sub_query_list  → list of sub-questions to dispatch
    hybrid.depth           → passed to each sub-state for depth guard
    hybrid.total_sub_q     → sanity check

References:
    plan/state.py     → is_sub_query_call, parent_sub_query, HybridPathState
    plan/README.md    → "Dispatch Sub Queries / Parallel Execution" section
    plan/work Phase.txt → Phase 5: LangGraph Send API
"""

import sys
from pathlib import Path
from typing import List, Union, Dict, Any

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState, new_sql_query_state, new_sql_retrieve_state, new_web_search_state
from langgraph.types import Send


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def dispatch_sub_queries_node(state: RAGState) -> List[Send]:
    """Fan out each sub-question as an independent parallel graph invocation.

    Returns a list of Send objects — LangGraph's mechanism for parallel
    map-reduce execution. Each Send targets 'rewrite_query' (the graph entry)
    with a fresh state built around a single sub-question.

    Input  : state.hybrid.{sub_query_list, depth}
    Output : List[Send] — one per sub-question
    """
    hybrid_state = state.get("hybrid", {})
    sub_query_list: List[str] = hybrid_state.get("sub_query_list", [])
    current_depth: int = hybrid_state.get("depth", 1)

    if not sub_query_list:
        print("[dispatch_sub_queries] No sub-questions to dispatch.")
        # Return an empty list — graph will route to append_sub_answer which
        # will detect total_sub_q == 0 and skip directly to merge.
        return []

    sends: List[Send] = []
    for sub_q in sub_query_list:
        # Build a clean, isolated state for this sub-query branch.
        # The sub-query starts from the beginning of the pipeline (rewrite_query).
        sub_state: RAGState = {
            # Identify this run as a sub-query so every path's terminal node
            # knows to call append_sub_answer instead of printing a final answer.
            "is_sub_query_call": True,
            "parent_sub_query": sub_q,

            # The sub-question IS the user input for this branch
            "user_input": sub_q,
            "rewritten_query": "",  # rewrite_query node will fill this

            # The depth is inherited so hybrid_depth_check can block recursion
            "hybrid": {
                "depth": current_depth,
                "total_sub_q": 0,
                "sub_query_list": [],
                "sub_query_ans": [],
                "sub_ans_count": 0,
                "merge_retries": 0,
            },

            # Fresh path states — no bleed from parent
            "sql_query": new_sql_query_state(),
            "sql_retrieve": new_sql_retrieve_state(),
            "web_search": new_web_search_state(),

            # Placeholder top-level fields
            "decided_path": "sql_retrieve",   # router will override
            "confidence_score": 0.0,
            "final_answer": "",
            "answer_status": "pending",
        }

        # Send this sub-state to the graph's entry node
        sends.append(Send("rewrite_query", sub_state))
        print(f"[dispatch_sub_queries] Dispatching: '{sub_q[:80]}'")

    print(f"[dispatch_sub_queries] Total dispatched: {len(sends)} sub-queries.")
    return sends


# =============================================================================
# Example Usage (non-graph test)
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে এবং এই সপ্তাহের নোটিশ কী?",
        "rewritten_query": "CSE বিভাগের প্রধান এবং এই সপ্তাহের নোটিশ",
        "hybrid": {
            "depth": 1,
            "total_sub_q": 2,
            "sub_query_list": [
                "CSE বিভাগের প্রধান কে?",
                "এই সপ্তাহে কোন নোটিশ প্রকাশিত হয়েছে?",
            ],
            "sub_query_ans": [],
            "sub_ans_count": 0,
            "merge_retries": 0,
        },
        "is_sub_query_call": False,
        "parent_sub_query": None,
        "sql_query": {},
        "sql_retrieve": {},
        "web_search": {},
        "decided_path": "hybrid",
        "confidence_score": 0.85,
        "final_answer": "",
        "answer_status": "pending",
    }

    sends = dispatch_sub_queries_node(sample_state)
    print(f"\nReturned {len(sends)} Send objects:")
    for s in sends:
        print(f"  → node={s.node!r}, user_input={s.arg.get('user_input')!r}")
