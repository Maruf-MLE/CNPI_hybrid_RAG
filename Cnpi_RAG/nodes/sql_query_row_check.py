"""
SQL Query Row Check Node - Phase 2
====================================

Checks the row count returned from the database call and routes accordingly.
Optimization (multi-row context) is handled by a separate node.

Routing decisions (made in graph.py):
    row_count = 0  → fallback_dispatcher  (no data → SQL Retrieve)
    row_count = 1  → sub_query_router_node (single row, ready for LLM directly)
    row_count > 1  → sql_query_optimize   (multiple rows, need context optimisation first)
"""

import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
for _p in [str(plan_root), str(project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state import RAGState


def sql_query_row_check_node(state: RAGState) -> Dict[str, Any]:
    """Read row_count from state — no transformation, just pass-through.

    The routing logic lives in graph.py (_route_after_row_check).
    This node only prints a diagnostic and returns state unchanged
    so the graph edge function can inspect row_count cleanly.
    """
    sql_query_state = state.get("sql_query", {})
    row_count = sql_query_state.get("row_count", 0)

    print(f"[sql_query_row_check] row_count = {row_count}")

    # No state mutation — the routing edge in graph.py reads row_count directly.
    return {}


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "sql_query": {
            "row_count": 3,
            "raw_context": "id:1 name:CSE | id:2 name:EEE | id:3 name:TE",
        }
    }
    result = sql_query_row_check_node(sample_state)
    print("Row check node output:", result)
