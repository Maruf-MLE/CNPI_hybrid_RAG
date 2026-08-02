"""
Merge Support Check Node - Phase 5
======================================

Validate that the merged answer is actually supported by the collected
sub-answer contexts. Mirrors the support-check pattern used in Phases 2-4.

Flow:
    state.final_answer + hybrid.sub_query_ans (contexts)
        → LLM validation
        → is_supported?
            Yes → answer_status = "found"  → END (graph prints final answer)
            No  → hybrid.merge_retries++   → merge_retry_check (retry gate)

State read:
    state.final_answer        (merged answer to validate)
    state.user_input          (original question for context)
    hybrid.sub_query_ans      (source contexts for validation)
    hybrid.merge_retries      (retry counter)

State written:
    state.answer_status       ("found" | "not_found")
    hybrid.merge_retries      (incremented on failure)

References:
    plan/state.py → HybridPathState.merge_retries, MAX_RETRIES
    plan/README.md → "Final Validation" section
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

from pydantic import BaseModel, Field

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState, SubQueryAnswer, MAX_RETRIES
from utils.llm_utils import get_llm
from langchain_core.prompts import ChatPromptTemplate


from typing import Literal

# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class MergeSupportCheckOutput(BaseModel):
    support_status: Literal["yes", "no_support", "hallucination"] = Field(
        description=(
            "'yes' if answer is fully supported. "
            "'no_support' if the evidences completely lack the answer. "
            "'hallucination' if evidence has info but answer is factually wrong."
        )
    )
    reason: str = Field(description="One-sentence reasoning.")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_MERGE_SUPPORT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a quality validator for a college information retrieval system.

Given an original question, the source evidence (sub-answers with their contexts),
and a merged final answer, determine whether the merged answer is accurate.

Return ONLY valid JSON matching the schema.
Choose support_status:
- 'yes': The merged answer uses only verifiable facts from the evidence.
- 'no_support': The evidence completely lacks information to answer the question.
- 'hallucination': The merged answer introduces new claims not in the evidence or contradicts it.
""",
    ),
    (
        "human",
        "Original Question:\n{question}\n\n"
        "Source Evidence:\n{evidence}\n\n"
        "Merged Answer:\n{merged_answer}",
    ),
])


def _build_evidence_text(sub_answers: List[SubQueryAnswer]) -> str:
    """Format sub-answers and their contexts as validation evidence."""
    parts = []
    for i, sa in enumerate(sub_answers, 1):
        ctx = sa.get("context") or "(no context)"
        parts.append(
            f"[Evidence {i}]\n"
            f"Sub-question : {sa.get('query', '')}\n"
            f"Answer       : {sa.get('final_answer', '')}\n"
            f"Context      : {ctx[:400]}\n"
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def merge_support_check_node(state: RAGState) -> Dict[str, Any]:
    """Validate the merged answer against the source sub-answer evidence.

    Input  : state.final_answer, state.hybrid.sub_query_ans, state.user_input
    Output : state.answer_status, hybrid.merge_retries
    """
    llm = get_llm()
    chain = _MERGE_SUPPORT_PROMPT | llm.with_structured_output(MergeSupportCheckOutput)

    hybrid_state = state.get("hybrid", {})
    merged_answer: str = state.get("final_answer", "").strip()
    user_input: str = state.get("user_input", "")
    sub_answers: List[SubQueryAnswer] = hybrid_state.get("sub_query_ans", [])
    merge_retries: int = hybrid_state.get("merge_retries", 0)

    # Guard: retry cap already hit
    if merge_retries >= MAX_RETRIES:
        print(f"[merge_support_check] Retry cap ({MAX_RETRIES}) reached — finalizing.")
        return {
            "answer_status": "not_found",
            "hybrid": {**hybrid_state, "merge_retries": merge_retries},
        }

    # Guard: no merged answer
    if not merged_answer:
        return {
            "answer_status": "not_found",
            "hybrid": {**hybrid_state, "merge_retries": merge_retries + 1},
        }

    evidence_text = _build_evidence_text(sub_answers)

    try:
        result: MergeSupportCheckOutput = chain.invoke({
            "question": user_input,
            "evidence": evidence_text or "(no evidence provided)",
            "merged_answer": merged_answer,
        })

        if result.support_status == "yes":
            print(f"[merge_support_check] ✅ Supported. Reason: {result.reason}")
            return {
                "answer_status": "found",
                "hybrid": {**hybrid_state, "merge_retries": merge_retries},
            }
        elif result.support_status == "no_support":
            print(f"[merge_support_check] No support in evidence. Skipping retries.")
            return {
                "answer_status": "not_found",
                "hybrid": {**hybrid_state, "merge_retries": MAX_RETRIES},
            }
        else:
            new_retries = merge_retries + 1
            print(
                f"[merge_support_check] ❌ Hallucination (retry {new_retries}/{MAX_RETRIES}). "
                f"Reason: {result.reason}"
            )
            return {
                "answer_status": "not_found",
                "hybrid": {**hybrid_state, "merge_retries": new_retries},
            }

    except Exception as e:
        print(f"[merge_support_check] LLM error: {e}")
        new_retries = merge_retries + 1
        return {
            "answer_status": "not_found",
            "hybrid": {**hybrid_state, "merge_retries": new_retries},
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে এবং এই সপ্তাহের নোটিশ কী?",
        "final_answer": (
            "CSE বিভাগের প্রধান হলেন ড. রহিম। "
            "এই সপ্তাহে পরীক্ষার তফসিল সংক্রান্ত নোটিশ প্রকাশিত হয়েছে।"
        ),
        "hybrid": {
            "depth": 1,
            "total_sub_q": 2,
            "sub_query_list": [],
            "sub_query_ans": [
                {
                    "query": "CSE বিভাগের প্রধান কে?",
                    "context": "Name: Dr. Rahim, Role: Head of CSE",
                    "final_answer": "CSE বিভাগের প্রধান হলেন ড. রহিম।",
                    "source_path": "sql_query",
                },
                {
                    "query": "এই সপ্তাহে কোন নোটিশ?",
                    "context": "Notice: ২০২৬ সালের পরীক্ষার তফসিল প্রকাশিত।",
                    "final_answer": "পরীক্ষার তফসিল নোটিশ প্রকাশিত হয়েছে।",
                    "source_path": "sql_retrieve",
                },
            ],
            "sub_ans_count": 2,
            "merge_retries": 0,
        },
        "answer_status": "pending",
    }

    result = merge_support_check_node(sample_state)
    print(f"Answer Status : {result.get('answer_status')}")
    print(f"Merge Retries : {result.get('hybrid', {}).get('merge_retries')}")
