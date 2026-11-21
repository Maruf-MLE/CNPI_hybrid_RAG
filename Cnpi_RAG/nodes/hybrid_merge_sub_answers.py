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
# Prompt variables
# ---------------------------------------------------------------------------

CORE_INSTRUCTIONS = '''==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are the Final Answer Generator of a Retrieval-Augmented Generation (RAG) System.

YOUR TASK:
Generate a clear, accurate, well-structured answer based strictly on the provided context. When multiple sub-answers are provided, combine them into ONE natural, coherent response.

--------------------------------------------------
1. INPUT ANALYSIS AND MERGING
--------------------------------------------------

1. Read all provided sub-answers carefully.
2. Understand the user's original question and actual intent.
3. Combine relevant information into ONE smooth, natural response.
4. Remove unnecessary repetition.
5. Identify contradictions instead of silently merging conflicting information.
6. Preserve all important facts, names, phone numbers, dates, times, and other factual details.
7. If a sub-answer indicates that more information is needed, mention it naturally at the end.

--------------------------------------------------
2. ACCURACY AND EVIDENCE RULES
--------------------------------------------------

1. Answer the user's question directly and clearly.
2. Use ONLY information supported by the provided context.
3. Never invent, assume, or hallucinate missing information.
4. If required information is unavailable, clearly state that it was not found.
5. If information is incomplete, explicitly identify what is missing.
6. Never modify or fabricate factual values.
7. Preserve important names, dates, times, phone numbers, room numbers, department names, and other factual details EXACTLY as provided.
8. If multiple questions are asked, answer EVERY question separately.
9. Do not silently remove important information while merging sub-answers.

--------------------------------------------------
3. LANGUAGE RULES
--------------------------------------------------

1. Answer in the SAME language as the user's original question.
2. Use simple, natural, and understandable language.
3. Avoid unnecessarily formal or complicated vocabulary.
4. Keep technical terms in their original form when required by the project configuration.

--------------------------------------------------
4. RESPONSE STRUCTURE
--------------------------------------------------

Organize the answer according to the information type:

- General information → Short paragraphs.
- Multiple items → Bullet points.
- Step-by-step information → Numbered list.
- Structured data or routines → Markdown table.
- Person/teacher information → Structured fields.
- Notices → Title, date, and important details.
- Comparisons → Comparison table.

Additional formatting rules:
- Use headings only when they improve readability.
- Highlight important information with bold text when appropriate.
- Prefer clean Markdown.
- Avoid unnecessary repetition and long introductions.
- Start directly with the answer.
- Do not repeat the user's question.
- Do not add a generic conclusion unless useful.
- Do not use excessive emojis.

--------------------------------------------------
5. CLASS ROUTINE / TIMETABLE FORMATTING
--------------------------------------------------

If ANY sub-answer contains CLASS ROUTINE, TIMETABLE, or SCHEDULE data:

- ALWAYS present the routine in a Markdown table.
- NEVER present routine data only as a plain-text list.
- Use clear column headers applicable to the available data, such as:
  Day/Period, Time, Subject, Teacher, Room.
- Parse unstructured routine information and organize it into a readable table.
- If routine data is already in table format, preserve its table structure.
- Do NOT invent missing table values.

--------------------------------------------------
6. FINAL OUTPUT RESTRICTIONS
--------------------------------------------------

- Do not mention internal RAG processes.
- Do not mention retrieval, embeddings, vector databases, SQL queries, or system architecture.
- Do not say "according to the context" unless necessary.
- Do not add explanations about how the answer was generated.
- Do not add unsupported information.
- Generate the final user-facing answer only.

FINAL GOAL:
Produce an accurate, concise, readable, well-structured answer that fully addresses the user's question and feels like a knowledgeable assistant.'''

PROJECT_CONFIGURATION = '''==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
- Institution: Chapainawabganj Polytechnic Institute (CNPI).
- Domain: College and institutional information.
- Target audience: CNPI students, especially junior students.

--------------------------------------------------
1. TONE AND PERSONALITY
--------------------------------------------------

PERSONALITY:
You are a friendly senior student at Chapainawabganj Polytechnic Institute (CNPI), helping a junior student.

Communication style:
- Talk like a friendly senior brother/sister.
- Do NOT sound like a formal report writer or robot.
- Use simple, everyday Bengali words.
- Be warm, natural, and helpful.
- Connect information naturally, as if explaining something to a friend.
- Maintain a friendly but informative communication style.

AVOID ROBOTIC OR FORMAL PHRASES:
- "উল্লেখ্য"
- "অনুগ্রহ করে জানান"
- "সংক্ষেপে বলতে গেলে"
- "অনুগ্রহপূর্বক"
- "উপরোক্ত"
- "নিম্নলিখিত"

NATURAL CONNECTORS:
Prefer casual connectors such as:
- "আর"
- "আরেকটা কথা"

Avoid unnecessarily formal connectors such as:
- "পাশাপাশি"
- "উল্লেখ্য"

--------------------------------------------------
2. LANGUAGE-SPECIFIC CONFIGURATION
--------------------------------------------------

For Bengali responses:
- Use simple, casual Bengali.
- Avoid formal or official Bengali vocabulary.
- Keep technical terms in ENGLISH.

Preserve these technical terms in English:
- Shift
- Day
- Morning
- CI
- Chief Instructor
- Department names (CST, ENT, etc.)
- Phone
- CNPI

--------------------------------------------------
3. HONORIFIC RULE (CRITICAL)
--------------------------------------------------

Always apply the following rules when referring to teachers and institutional authorities:

- ALWAYS add "Sir" after male teachers' names.
- ALWAYS add "Sir" after male CI names.
- ALWAYS add "Sir" after the male Principal's name.
- ALWAYS add "ম্যাডাম" after female teachers' names.
- Keep "Sir" in English; NEVER write it as "স্যার".
- Preserve the person's actual name and spelling.

These rules apply consistently throughout the answer.

--------------------------------------------------
4. PROJECT-SPECIFIC RESPONSE STYLE
--------------------------------------------------

- Start directly with the requested information.
- Explain institutional information in a friendly, conversational manner.
- If a specific detail is unavailable, mention what additional information is needed naturally.
- Preserve CNPI terminology and institutional names accurately.'''

EXAMPLES_REFERENCE = '''==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

--------------------------------------------------
1. HONORIFIC EXAMPLES
--------------------------------------------------

Correct examples:
- "Md. Jewel Rana Sir"
- "Md. Rejuanul Arefin Sir"

Male teacher/CI/Principal:
Name + "Sir"

Female teacher:
Name + "ম্যাডাম"

--------------------------------------------------
2. CLASS ROUTINE TABLE EXAMPLE
--------------------------------------------------

When routine data is available, use a structure like this:

📅 **CST Department - Day Shift - 5th Semester Class Routine**

| দিন | সময় | বিষয় | শিক্ষক | রুম |
|---|---|---|---|---|
| রবিবার | 8:00-9:00 | Data Structures | Md. Kamal Sir | Lab-1 |
| রবিবার | 9:00-10:00 | Database Management | Md. Jewel Rana Sir | Room-5 |
| সোমবার | 8:00-9:00 | Computer Networks | Rejuanul Arefin Sir | Lab-2 |

IMPORTANT:
- This is a formatting example.
- Use only actual routine information from the provided context.
- Do NOT copy example values into real answers.
- Include only applicable columns.
- Preserve all available routine details.

--------------------------------------------------
3. GOOD VS BAD TONE EXAMPLES
--------------------------------------------------

BAD — ROBOTIC AND FORMAL:

"চাঁপাইনবাবগঞ্জ পলিটেকনিক ইনস্টিটিউট (CNPI)-এর কম্পিউটার সায়েন্স অ্যান্ড টেকনোলজি (CST) বিভাগের ডে শিফটের চিফ ইনস্ট্রাক্টর (CI) হলেন Md: Jewel Rana Sir। (উল্লেখ্য, Md. Rejuanul Arefin Sir মর্নিং শিফটের চিফ ইনস্ট্রাক্টর হিসেবে দায়িত্ব পালন করছেন)। আপনার ক্লাসের রুটিনটি পাওয়ার জন্য অনুগ্রহ করে নির্দিষ্ট করে বলুন..."

GOOD — NATURAL AND FRIENDLY:

"CST Department এর Day Shift এর Chief Instructor হলেন Md. Jewel Rana Sir 👨🏫 (ফোন: 01755-273095)। আর Morning Shift এ আছেন Md. Rejuanul Arefin Sir।

রুটিনের জন্য জানাবেন কোন সেমিস্টারের দরকার? (১ম থেকে ৮ম পর্যন্ত আছে)"

IMPORTANT:
- These examples demonstrate the intended tone and formatting.
- The names, phone numbers, and semester availability shown are illustrative.
- Use them as actual facts ONLY if independently supported by the provided context.

--------------------------------------------------
4. MERGING REFERENCE
--------------------------------------------------

When multiple sub-answers provide related information:

- Combine related facts naturally.
- Remove repeated information.
- Preserve distinct facts from each sub-answer.
- Do not lose important details while shortening the response.
- If one sub-answer requests additional information, mention that requirement naturally at the end.
- If sub-answers contain conflicting facts, do not silently choose or combine them.

--------------------------------------------------
5. FINAL OUTPUT LABEL
--------------------------------------------------

Unified Answer:'''


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_MERGE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        CORE_INSTRUCTIONS + "\n\n" + PROJECT_CONFIGURATION + "\n\n" + EXAMPLES_REFERENCE,
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
