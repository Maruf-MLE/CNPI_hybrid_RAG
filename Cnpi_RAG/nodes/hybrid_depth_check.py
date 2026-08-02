"""
Hybrid Depth Check Node - Phase 5
====================================

Guard node: ensures a Hybrid sub-query cannot recursively trigger another
Hybrid dispatch (preventing infinite loops).

Flow:
    hybrid.depth < MAX_HYBRID_DEPTH?
        Yes (depth == 0) → continue to create_sub_questions
        No  (depth >= 1) → fallback directly to sql_retrieve_check
                           (sub-queries are never allowed to be hybrid again)

State read:
    hybrid.depth  (defaults to 0 if missing)

State written:
    hybrid.depth  (incremented by 1 to track nesting level)

References:
    plan/state.py  → MAX_HYBRID_DEPTH = 1, HybridPathState.depth
    plan/work Phase.txt Phase 5 → hybrid_depth_check node
"""

import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState, MAX_HYBRID_DEPTH


def hybrid_depth_check_node(state: RAGState) -> Dict[str, Any]:
    """Check recursion depth before allowing Hybrid sub-query dispatch.

    Input  : state.hybrid.depth
    Output : state.hybrid.depth  (incremented)

    The ROUTING decision (continue vs fallback) is made by the conditional
    edge in graph.py that reads hybrid.depth AFTER this node runs.
    This node only increments the counter so the edge function sees the
    updated value.
    """
    hybrid_state = state.get("hybrid", {})
    current_depth = hybrid_state.get("depth", 0)

    # Increment depth to record that we are entering the Hybrid layer
    new_depth = current_depth + 1

    print(
        f"[hybrid_depth_check] depth: {current_depth} → {new_depth} "
        f"(MAX_HYBRID_DEPTH={MAX_HYBRID_DEPTH})"
    )

    return {
        "hybrid": {
            **hybrid_state,
            "depth": new_depth,
        }
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Simulate first call (top-level request)
    state_top = {
        "hybrid": {
            "depth": 0,
            "total_sub_q": 0,
            "sub_query_list": [],
            "sub_query_ans": [],
            "sub_ans_count": 0,
            "merge_retries": 0,
        }
    }

    result = hybrid_depth_check_node(state_top)
    print(f"Top-level depth → {result['hybrid']['depth']}")  # Expected: 1

    # Simulate second call (sub-query trying to be hybrid again)
    state_nested = {
        "hybrid": {**result["hybrid"], "depth": 1}
    }
    result2 = hybrid_depth_check_node(state_nested)
    print(f"Nested depth → {result2['hybrid']['depth']}")   # Expected: 2 (> MAX → fallback)
