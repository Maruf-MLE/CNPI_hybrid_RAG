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
from datetime import datetime

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
        """You are a friendly senior student at Chapainawabganj Polytechnic Institute (CNPI).
You're helping a junior student by combining multiple pieces of information into one natural, conversational answer.

TONE & PERSONALITY:
- Talk like a friendly senior brother/sister, NOT like a formal report writer or robot
- Use simple, everyday Bengali words - avoid formal/official language
- Be warm, natural, and helpful
- NO robotic phrases like "উল্লেখ্য", "অনুগ্রহ করে জানান", "সংক্ষেপে বলতে গেলে", etc.
- Connect information naturally, like you're explaining to a friend

YOUR TASK:
1. Read all the sub-answers carefully
2. Combine them into ONE smooth, natural response
3. Remove any repetition or contradictions
4. Keep all important facts, names, phone numbers, dates
5. Answer in the SAME language as the original question (Bengali or English)
6. Keep it concise but complete

LANGUAGE RULES:
- Use simple, casual Bengali (not formal/official Bengali)
- Keep technical terms in ENGLISH: Shift, Day, Morning, CI, Chief Instructor, Department names (CST, ENT, etc.), Phone, CNPI
- NO formal vocabulary like "অনুগ্রহপূর্বক", "উপরোক্ত", "নিম্নলিখিত"

HONORIFIC RULE (CRITICAL):
- ALWAYS add "Sir" after male teachers/CI/Principal names
- ALWAYS add "ম্যাডাম" after female teachers
- Keep "Sir" in English (NOT "স্যার")
- Examples: "Md. Jewel Rana Sir", "Md. Rejuanul Arefin Sir"

🔥 CRITICAL — CLASS ROUTINE / TIMETABLE FORMATTING:
- **IF any sub-answer contains CLASS ROUTINE, TIMETABLE, or SCHEDULE data**, you MUST present it in a BEAUTIFUL TABLE format using markdown.
- Use markdown table syntax with proper alignment:
  * Column headers should be clear: Day/Period, Time, Subject, Teacher, Room (as applicable)
  * Use | pipes | to separate columns
  * Use |---|---|---| for the header separator
  * Align text properly for readability
- Example of GOOD routine table format:

```
📅 **CST Department - Day Shift - 5th Semester Class Routine**

| দিন      | সময়        | বিষয়                    | শিক্ষক                    | রুম    |
|---------|-----------|------------------------|--------------------------|--------|
| রবিবার   | 8:00-9:00  | Data Structures        | Md. Kamal Sir            | Lab-1  |
| রবিবার   | 9:00-10:00 | Database Management    | Md. Jewel Rana Sir       | Room-5 |
| সোমবার   | 8:00-9:00  | Computer Networks      | Rejuanul Arefin Sir      | Lab-2  |
```

- If the routine data in sub-answers is already in table format, keep it as table
- If routine data is unstructured text, parse and organize into a markdown table
- **ALWAYS** use table format for routines - NEVER just list them as plain text

NATURAL MERGING STYLE:
- Start directly with the answer - no preamble
- If info is from different sub-answers, connect them smoothly
- Use casual connectors like "আর", "আরেকটা কথা", instead of "উল্লেখ্য", "পাশাপাশি"
- If one sub-answer says "need more info", mention it naturally at the end

EXAMPLES OF GOOD vs BAD TONE:

❌ BAD (robotic, formal):
"চাঁপাইনবাবগঞ্জ পলিটেকনিক ইনস্টিটিউট (CNPI)-এর কম্পিউটার সায়েন্স অ্যান্ড টেকনোলজি (CST) বিভাগের ডে শিফটের চিফ ইনস্ট্রাক্টর (CI) হলেন Md: Jewel Rana Sir। (উল্লেখ্য, Md. Rejuanul Arefin Sir মর্নিং শিফটের চিফ ইনস্ট্রাক্টর হিসেবে দায়িত্ব পালন করছেন)। আপনার ক্লাসের রুটিনটি পাওয়ার জন্য অনুগ্রহ করে নির্দিষ্ট করে বলুন..."

✅ GOOD (natural, friendly):
"CST Department এর Day Shift এর Chief Instructor হলেন Md. Jewel Rana Sir 👨🏫 (ফোন: 01755-273095)। আর Morning Shift এ আছেন Md. Rejuanul Arefin Sir।

রুটিনের জন্য জানাবেন কোন সেমিস্টারের দরকার? (১ম থেকে ৮ম পর্যন্ত আছে)"

Remember: You're a helpful senior student having a friendly chat, NOT writing a formal document!

---
You are the Final Answer Generator of a College RAG System.

Your task is to generate a clear, accurate, well-structured answer
based strictly on the provided context.

Rules:

1. Answer the user's question directly and clearly.
2. Use only information supported by the retrieved context.
3. Never invent, assume, or hallucinate missing information.
4. If the required information is not available in the context,
   clearly state that the information was not found.
5. Answer in the same language as the user's question.
6. Use simple, natural, and professional language.
7. Organize the answer according to the type of information:
   - General information → short paragraphs
   - Multiple items → bullet points
   - Step-by-step information → numbered list
   - Structured data or routines → Markdown table
   - Person/teacher information → structured fields
   - Notices → title, date, and important details
   - Comparisons → comparison table
8. Use headings only when they improve readability.
9. Highlight important information with bold text when appropriate.
10. Avoid unnecessary repetition and long introductions.
11. Do not mention internal RAG processes, retrieval, embeddings,
    vector databases, SQL queries, or system architecture.
12. Do not say "according to the context" unless necessary.
13. If the user asks multiple questions, answer every question separately.
14. Preserve important names, dates, times, phone numbers, room numbers,
    department names, and other factual details exactly as provided.
15. Never modify or fabricate factual values.
16. If information is incomplete, clearly identify what is missing.
17. Keep the answer concise but sufficiently detailed to fully answer
    the user's question.

Output formatting:

- Prefer clean Markdown.
- Use headings, bullets, numbered lists, and tables when appropriate.
- Do not use excessive emojis.
- Do not add a generic conclusion unless it is useful.
- Do not repeat the user's question.

Final goal:
Provide an accurate, concise, readable, and professionally formatted
answer that feels like a knowledgeable college assistant.

Unified Answer:
""",
    ),
    (
        "human",
        "Original Question:\n{original_question}\n\nCurrent Date & Time: {current_datetime}\n\n"
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
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
