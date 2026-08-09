"""
Merge Sub Answers Node - Phase 5
=====================================

Use the LLM to combine all collected sub-query answers into a single, coherent,
unified final response.

Flow:
    hybrid.sub_query_ans (list of SubQueryAnswer)
        → LLM merge
        → state.final_answer  (top-level unified answer)

Design Notes:
- Deduplicates any repeated information before feeding to LLM.
- Each sub-answer is formatted with its sub-question for context.
- The merged answer is written to TOP-LEVEL state.final_answer so the
  Django view and merge_support_check can read it without path knowledge.
- merge_retries is NOT incremented here — that happens in merge_retry_check
  if the support check fails.

State read:
    hybrid.sub_query_ans   → list of SubQueryAnswer records
    state.user_input       → original question (for coherent framing)

State written:
    state.final_answer     (top-level unified answer)
    hybrid.sub_query_ans   (unchanged — kept for audit/logging)

References:
    plan/state.py → SubQueryAnswer, HybridPathState.merge_retries
    plan/README.md → "Answer Merge" section
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState, SubQueryAnswer
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_MERGE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert at synthesizing multiple answers into one coherent response
for Chapainawabganj Polytechnic Institute (CNPI) information queries.

Instructions:
1. You will receive the original complex question and several sub-answers.
2. Merge them into ONE unified, well-structured response.
3. Eliminate redundancy and contradictions.
4. Preserve all important facts, dates, names, and details.
5. Respond in the SAME language as the original question (Bengali or English).
6. Keep the response concise but complete.
7. Do NOT add information not present in the sub-answers.

HONORIFIC RULE — VERY IMPORTANT:
8. Whenever you mention a person who is a Principal, Vice Principal, Chief Instructor (CI),
   Instructor, or Teacher, you MUST address them with "Sir" (or "ম্যাডাম" for female teachers)
   as a sign of respect. This applies EVERY time the person's name is mentioned.
   - For male: add "Sir" after the name (e.g., "Md. Rejuanul Arefin Sir")
   - For female: add "ম্যাডাম" after the name (e.g., "Mosa: Roshana Khatun ম্যাডাম")
   - Keep "Sir" in English (do not write "স্যার").
   - ALWAYS use "Sir"/"ম্যাডাম" — never omit it when mentioning a teacher/CI/Principal by name.
""",
    ),
    (
        "human",
        "Original Question:\n{original_question}\n\n"
        "Sub-Answers to Merge:\n{sub_answers_text}\n\n"
        "Unified Answer:",
    ),
])


def _format_sub_answers(sub_answers: List[SubQueryAnswer]) -> str:
    """Format sub-answers into a readable block for the LLM."""
    lines = []
    for i, sa in enumerate(sub_answers, start=1):
        lines.append(
            f"[Sub-Answer {i}]\n"
            f"Sub-Question : {sa.get('query', '')}\n"
            f"Path Used    : {sa.get('source_path', 'unknown')}\n"
            f"Answer       : {sa.get('final_answer', '(no answer)')}\n"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def merge_sub_answers_node(state: RAGState) -> Dict[str, Any]:
    """Merge all collected sub-answers into a single unified response.

    Input  : state.hybrid.sub_query_ans, state.user_input
    Output : state.final_answer  (top-level)
    """
    llm = get_llm()
    chain = _MERGE_PROMPT | llm

    hybrid_state = state.get("hybrid", {})
    sub_answers: List[SubQueryAnswer] = hybrid_state.get("sub_query_ans", [])
    user_input: str = state.get("user_input", "")

    print(f"[merge_sub_answers] Merging {len(sub_answers)} sub-answers.")

    # Guard: nothing to merge
    if not sub_answers:
        fallback = (
            "দুঃখিত, কোনো উপ-প্রশ্নের উত্তর সংগ্রহ করা সম্ভব হয়নি।"
            if any(ord(c) > 127 for c in user_input)
            else "Sorry, no sub-answers were collected to merge."
        )
        return {
            "final_answer": fallback,
            "answer_status": "not_found",
        }

    # Single answer edge-case: no need for LLM merge
    if len(sub_answers) == 1:
        single_answer = sub_answers[0].get("final_answer", "")
        print("[merge_sub_answers] Only 1 sub-answer — using directly without LLM merge.")
        return {
            "final_answer": single_answer,
            "answer_status": "found" if single_answer.strip() else "not_found",
        }

    sub_answers_text = _format_sub_answers(sub_answers)

    try:
        response = chain.invoke({
            "original_question": user_input,
            "sub_answers_text": sub_answers_text,
        })

        merged = extract_content(response).strip()

        if not merged:
            raise ValueError("LLM returned empty merged response.")

        print(f"[merge_sub_answers] Merge complete. Length: {len(merged)} chars.")

        return {
            "final_answer": merged,
            "answer_status": "pending",  # support check will set to "found"
        }

    except Exception as e:
        print(f"[merge_sub_answers] LLM merge error: {e}")
        # Fallback: concatenate raw sub-answers
        fallback_parts = [
            f"{sa.get('query', '')}: {sa.get('final_answer', '')}"
            for sa in sub_answers
        ]
        fallback_answer = " | ".join(fallback_parts)
        return {
            "final_answer": fallback_answer,
            "answer_status": "pending",
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "user_input": "CSE বিভাগের প্রধান কে এবং এই সপ্তাহে কোন নোটিশ প্রকাশিত হয়েছে?",
        "hybrid": {
            "depth": 1,
            "total_sub_q": 2,
            "sub_query_list": [
                "CSE বিভাগের প্রধান কে?",
                "এই সপ্তাহে কোন নোটিশ প্রকাশিত হয়েছে?",
            ],
            "sub_query_ans": [
                {
                    "query": "CSE বিভাগের প্রধান কে?",
                    "context": "Name: Dr. Rahim, Dept: CSE, Role: Head",
                    "final_answer": "CSE বিভাগের প্রধান হলেন ড. রহিম।",
                    "source_path": "sql_query",
                },
                {
                    "query": "এই সপ্তাহে কোন নোটিশ প্রকাশিত হয়েছে?",
                    "context": "Notice: পরীক্ষা তফসিল ২০২৬ — Date: 2026-07-20",
                    "final_answer": "এই সপ্তাহে পরীক্ষার তফসিল সম্পর্কিত নোটিশ প্রকাশিত হয়েছে।",
                    "source_path": "sql_retrieve",
                },
            ],
            "sub_ans_count": 2,
            "merge_retries": 0,
        },
        "final_answer": "",
        "answer_status": "pending",
    }

    result = merge_sub_answers_node(sample_state)
    print("Merged Answer:")
    print(result.get("final_answer"))
    print(f"Answer Status: {result.get('answer_status')}")
