"""
Merge Retry Check Node - Phase 5
=====================================

Final gate in the Hybrid path. Decides whether to:
    a) Re-trigger the merge (go back to merge_sub_answers) if retries remain, OR
    b) Accept the current answer as the final response (END).

This is the last node before the Hybrid path terminates.

Flow:
    answer_status == "found"?
        Yes → END (final_answer already set, Django view reads it)
    answer_status == "not_found" AND merge_retries < MAX_RETRIES?
        → merge_sub_answers (retry the LLM merge)
    merge_retries >= MAX_RETRIES?
        → END (set answer_status = "not_found", write exhaustion message)

State read:
    state.answer_status      ("found" | "not_found")
    hybrid.merge_retries     (current retry count)

State written:
    state.final_answer       (possibly overwritten with "not_found" message)
    state.answer_status      (finalized)

Note:
    The routing decision (merge_sub_answers vs END) is implemented as a
    conditional edge in graph.py that reads these values AFTER this node runs.
    This node's job is only to finalize state for logging/display — routing
    is the edge function's responsibility.

References:
    plan/state.py → MAX_RETRIES, HybridPathState.merge_retries
    plan/work Phase.txt Phase 5 → merge_retry_check node
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

from state import RAGState, MAX_RETRIES


def merge_retry_check_node(state: RAGState) -> Dict[str, Any]:
    """Gate node: finalize state for either retry or termination.

    Input  : state.answer_status, hybrid.merge_retries, state.final_answer
    Output : state.final_answer (updated if exhausted), state.answer_status
    """
    hybrid_state = state.get("hybrid", {})
    merge_retries: int = hybrid_state.get("merge_retries", 0)
    answer_status: str = state.get("answer_status", "not_found")
    user_input: str = state.get("user_input", "")
    current_answer: str = state.get("final_answer", "").strip()

    print(
        f"[merge_retry_check] answer_status={answer_status}, "
        f"merge_retries={merge_retries}/{MAX_RETRIES}"
    )

    # ── Case 1: answer is good ─────────────────────────────────────────────
    if answer_status == "found":
        print("[merge_retry_check] ✅ Answer accepted — routing to END.")
        return {
            "answer_status": "found",
            "final_answer": current_answer,
        }

    # ── Case 2: retries still available — signal the edge to loop back ─────
    if merge_retries < MAX_RETRIES:
        print(
            f"[merge_retry_check] Retry {merge_retries}/{MAX_RETRIES} — "
            "routing to merge_sub_answers."
        )
        # No state change here; graph edge will route back to merge_sub_answers
        return {
            "answer_status": "not_found",
        }

    # ── Case 3: retries exhausted — finalize with "not_found" message ──────
    print(f"[merge_retry_check] ❌ Retries exhausted ({MAX_RETRIES}) — finalizing.")
    exhaustion_msg = (
        "একাধিক চেষ্টার পরেও সন্তোষজনক উত্তর তৈরি করা সম্ভব হয়নি। "
        "অনুগ্রহ করে প্রশ্নটি ভিন্নভাবে করুন।"
        if any(ord(c) > 127 for c in user_input)
        else (
            f"A satisfactory merged answer could not be generated after "
            f"{MAX_RETRIES} attempts. Please rephrase your question."
        )
    )
    return {
        "final_answer": exhaustion_msg,
        "answer_status": "not_found",
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Scenario 1: answer accepted
    state_found: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে?",
        "final_answer": "CSE বিভাগের প্রধান হলেন ড. রহিম।",
        "answer_status": "found",
        "hybrid": {"merge_retries": 0},
    }
    r1 = merge_retry_check_node(state_found)
    print(f"Scenario 1 — status: {r1['answer_status']}, answer: {r1['final_answer'][:50]}")

    # Scenario 2: first retry
    state_retry: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে?",
        "final_answer": "উত্তর পাওয়া যায়নি।",
        "answer_status": "not_found",
        "hybrid": {"merge_retries": 1},
    }
    r2 = merge_retry_check_node(state_retry)
    print(f"Scenario 2 — status: {r2['answer_status']}")  # not_found, loop back

    # Scenario 3: exhausted
    state_exhausted: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে?",
        "final_answer": "",
        "answer_status": "not_found",
        "hybrid": {"merge_retries": 3},
    }
    r3 = merge_retry_check_node(state_exhausted)
    print(f"Scenario 3 — status: {r3['answer_status']}, answer: {r3['final_answer'][:60]}")
