"""
SQL Query Optimize Node - Phase 2
=====================================

Called ONLY when row_count > 1 (multiple rows returned from DB).
Merges and prioritises raw context rows into a compact, LLM-friendly string.

Single-row results skip this node entirely and go straight to
sub_query_router_node (then LLM response).

Flow:
    sql_query.raw_context  →  sql_query.optimized_context
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
for _p in [str(plan_root), str(project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state import RAGState


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _format_optimized_context(rows_data: List[str], importance_tags: List[str]) -> str:
    """Merge rows into a structured, LLM-friendly context block."""
    lines = []
    if importance_tags:
        lines.append("### Context Details")
        lines.append(f"### Importance: {', '.join(importance_tags)}")
        lines.append("")
    for idx, row_text in enumerate(rows_data, 1):
        lines.append(f"--- Row {idx} ---")
        lines.append(row_text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def sql_query_optimize_node(state: RAGState) -> Dict[str, Any]:
    """Combine multiple DB rows into an optimised context string.

    Input  : sql_query.raw_context, sql_query.row_count
    Output : sql_query.optimized_context
    """
    sql_query_state = state.get("sql_query", {})
    row_count: int = sql_query_state.get("row_count", 0)
    raw_context: str = sql_query_state.get("raw_context", "")

    print(f"[sql_query_optimize] Optimising context for {row_count} rows.")

    optimized_context = _format_optimized_context(
        rows_data=[raw_context],
        importance_tags=["priority_high", "date_important"],
    )

    return {
        "sql_query": {
            **sql_query_state,
            "optimized_context": optimized_context,
        }
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "sql_query": {
            "row_count": 3,
            "raw_context": (
                "id:1 name:CSE dept | id:2 name:EEE dept | id:3 name:TE dept"
            ),
        }
    }
    result = sql_query_optimize_node(sample_state)
    print("Optimized context:")
    print(result["sql_query"]["optimized_context"])
