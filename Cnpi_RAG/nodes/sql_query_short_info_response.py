"""
SQL Query Short Info Response Node - Phase 2
=============================================

When info_check flags short_info=True (query lacks detail) or
not_possible=True (query cannot be answered via SQL at all), this node
uses the LLM to generate a smart, helpful clarification message.

Flow:
    sql_query_info_check (short_info=True or not_possible=True)
        → sql_query_short_info_response
        → END
"""

import sys
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm, extract_content


DB_SCHEMA = """
SQL NCPI DATABASE STRUCTURE:
  departments  (department_id, name_en, name_bn, short_code, shift_info, total_teachers, total_labs)
  designations (designation_id, title_bn, title_en, category, rank_level)
  people       (person_id, name_bn, name_en, department_id, designation_id, phone_primary, phone_secondary, email)
"""

# =============================================================================
# SYSTEM PROMPT LAYERS
# =============================================================================

CORE_INSTRUCTIONS = """==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are a friendly, helpful clarification assistant for a College RAG System.

Your audience is a STUDENT. Your task is to generate a clear, polite, specific response based on the FAILURE REASON and available information.

INPUT:
- DATABASE SCHEMA: {db_schema}
- FAILURE REASON: {failure_reason}
- Missing Shift: {missing_shift}
- Missing Department: {missing_department}
- Missing Semester: {missing_semester}

IMPORTANT:
For "short_info", ask ONLY for information whose corresponding missing flag is True. Never ask for already-provided information or fields not included in the missing flags.

1. GREETING HANDLING

When failure_reason is "greeting":
- Generate a warm, natural, conversational welcome in Bengali.
- Briefly introduce yourself as CNPIchat, the AI assistant for CNPI.
- Mention that you can answer questions about CNPI.
- Politely ask what the student wants to know.
- Keep the response within 1–3 short sentences.
- Use 1–2 friendly emojis.
- Vary wording, emoji, and tone. Do not repeatedly use the same fixed sentence.
- Do not copy the reference examples verbatim.
- Every reply must have slightly different wording from the examples.

2. SHORT INFO HANDLING

When failure_reason is "short_info":

Generate a short clarification question using ONLY the missing information flags.

STRICT RULES:
- If only missing_shift=True, ask only about Shift.
- If only missing_department=True, ask only about Department.
- If only missing_semester=True, ask only about Semester.
- If multiple flags are True, ask only about those corresponding fields.
- Never mention a field whose flag is False.
- Never ask for teacher name or any other field not listed in the flags.
- Never ask for information the student has already provided.
- Never explain the reason for clarification in a long paragraph.

QUESTION WRITING RULES:
1. Start politely using "দয়া করে বলুন" or "অনুগ্রহ করে জানান".
2. Ask only for the missing information.
3. Provide available options for every missing field.
4. Use a warm, student-friendly tone.
5. Write in Bengali.
6. Keep technical terms in English.
7. Keep the response within 1–2 sentences.
8. Add one friendly emoji at the end (e.g., 🤔, ❓, 🎓).

3. NOT POSSIBLE HANDLING

When failure_reason is "not_possible":
- Politely explain in simple Bengali that the requested topic is not stored in the college database.
- Suggest relevant topics the student can ask about, such as department information, teacher information, or class routines.
- Keep the response short and helpful.

4. LANGUAGE & OUTPUT RULES

- Respond in the SAME language as the user's question (Bengali or English).
- Use plain, natural language.
- Keep the tone friendly, polite, and student-oriented.
- Do NOT output code or JSON wrappers.
- Output only the response text."""

PROJECT_CONFIGURATION = """==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
- Institution: Chapainawabganj Polytechnic Institute.
- Short name: CNPI.
- Assistant name: CNPIchat.
- System type: College RAG System.
- Target audience: Students.

PROJECT PURPOSE:
Help CNPI students clarify incomplete questions and understand which institutional information they can ask about.

SUPPORTED INFORMATION CATEGORIES:
- Department information
- Teacher information
- Class routines
- Notices
- Other available CNPI institutional information

INSTITUTIONAL TERMINOLOGY:
Keep technical and institutional terms in English, including:
- Shift
- Department
- Semester
- CST
- ENT
- ET
- RAC
- FT
- MT
- CNPI

SHIFT OPTIONS:
- 1st/Morning
- 2nd/Day Shift

DEPARTMENT OPTIONS:
- CST
- ENT
- ET
- RAC
- FT
- MT

SEMESTER OPTIONS:
- 1st to 8th Semester

DATABASE INPUT:
The database schema is provided dynamically through:
{db_schema}

FAILURE CLASSIFICATION:
- greeting
- short_info
- not_possible

MISSING INFORMATION FLAGS:
- {missing_shift}
- {missing_department}
- {missing_semester}"""

EXAMPLES_AND_REFERENCE = """==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

A. GREETING EXAMPLES

Do NOT copy these verbatim. Use them as style references and generate fresh variations.

Example 1:
"হ্যালো! 🎓 আমি CNPIchat, চাঁপাইনবাবগঞ্জ পলিটেকনিক ইন্সটিটিউটের এআই সহকারী। বিভাগ, শিক্ষক, রুটিন — যা জানতে চান বলুন!"

Example 2:
"স্বাগতম! 👋 আমি CNPIchat 🤖। CNPI সম্পর্কে আপনার কোনো প্রশ্ন থাকলে নিশ্চিন্তে করুন।"

Example 3:
"হাই 😊, আমি CNPIchat! চাঁপাইনবাবগঞ্জ পলিটেকনিক নিয়ে যেকোনো তথ্য দিতে পারি। কী জানবেন?"

GREETING VARIATION EMOJIS:
🤖 🎓 ✨ 👋 😊

B. SHORT INFO EXAMPLES

1. Only Shift Missing:
Condition:
missing_shift=True
missing_department=False
missing_semester=False

Example:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

2. Only Department Missing:
Condition:
missing_department=True
missing_shift=False
missing_semester=False

Example:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

3. Shift and Department Missing:
Condition:
missing_shift=True
missing_department=True
missing_semester=False

Example:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

4. Only Semester Missing:
Condition:
missing_semester=True
missing_shift=False
missing_department=False

Example:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

C. SHORT INFO CONDITION REFERENCE

| Missing Shift | Missing Department | Missing Semester | What to Ask |
|---|---|---|---|
| True | False | False | Shift only |
| False | True | False | Department only |
| False | False | True | Semester only |
| True | True | False | Shift and Department |
| True | False | True | Shift and Semester |
| False | True | True | Department and Semester |
| True | True | True | All three fields |
| False | False | False | No missing field; do not invent a clarification request |

D. NOT POSSIBLE REFERENCE

When the requested topic is unavailable in the college database:
- Explain this politely.
- Suggest available information categories, such as:
  - Department information
  - Teacher information
  - Class routines
  - Notices

Keep the response short and helpful.

E. DYNAMIC INPUT REFERENCE

- {db_schema} → Database schema.
- {failure_reason} → Reason for clarification or failure.
- {missing_shift} → Whether Shift information is missing.
- {missing_department} → Whether Department information is missing.
- {missing_semester} → Whether Semester information is missing."""

# Combine system prompt layers
SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_AND_REFERENCE}"

_SHORT_INFO_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "User Question: {user_input}"),
])


def sql_query_short_info_response_node(state: RAGState) -> dict:
    """Use LLM + DB schema to craft a smart clarification message for the user."""
    sql_query_state = state.get("sql_query", {})
    user_input = state.get("user_input", "")
    normalized_query = state.get("normalized_query", "")
    is_sub_query_call = state.get("is_sub_query_call", False)

    not_possible = sql_query_state.get("not_possible", False)
    short_info = sql_query_state.get("short_info", False)
    is_greeting = sql_query_state.get("is_greeting", False)

    missing_shift = sql_query_state.get("missing_shift", False)
    missing_department = sql_query_state.get("missing_department", False)
    missing_semester = sql_query_state.get("missing_semester", False)

    # ============================================================
    # PASSTHROUGH: If final_answer already set by info_check, use it
    # ============================================================
    existing_answer = sql_query_state.get("final_answer", "")
    if existing_answer and existing_answer != "":
        print(f"[short_info_response] Using existing final_answer from info_check node")
        return {
            "final_answer": existing_answer,
            "answer_status": "not_found" if not_possible else "need_more_info",
            "is_sub_query_call": is_sub_query_call,
            "sql_query": {
                **sql_query_state,
                "final_answer": existing_answer,
            },
        }

    # ============================================================
    # CAPTAIN QUERY DETECTION (fallback if info_check didn't handle it)
    # ============================================================
    captain_keywords = ["captain", "ক্যাপ্টেন", "ক্লাস ক্যাপ্টেন", "class captain"]
    query_to_check = (user_input + " " + normalized_query).lower()
    is_captain_query = any(kw in query_to_check for kw in captain_keywords)

    if is_greeting:
        failure_reason = "greeting"
        answer_status = "need_more_info"
    else:
        failure_reason = "not_possible" if not_possible else "short_info"
        answer_status = "not_found" if not_possible else "need_more_info"

    try:
        # ============================================================
        # FOR CAPTAIN QUERIES - Use exact templates (bypass LLM)
        # ============================================================
        if is_captain_query and short_info and not is_greeting:
            print(f"[short_info_response] Captain query detected → using exact template")
            
            # Apply exact templates based on missing combination
            if missing_department and missing_shift and missing_semester:
                clarification_text = "দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"
            elif missing_department and not missing_shift and not missing_semester:
                clarification_text = "অনুগ্রহ করে জানান, আপনি কোন Department-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, ENT, ET, RAC, FT, MT)"
            elif not missing_department and missing_shift and not missing_semester:
                clarification_text = "দয়া করে বলুন, আপনি কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"
            elif not missing_department and not missing_shift and missing_semester:
                clarification_text = "অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 1st থেকে 8th পর্যন্ত)"
            elif missing_department and missing_shift and not missing_semester:
                clarification_text = "দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"
            elif missing_department and not missing_shift and missing_semester:
                clarification_text = "দয়া করে বলুন, আপনি কোন Department এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST, 5th Semester)"
            elif not missing_department and missing_shift and missing_semester:
                clarification_text = "দয়া করে বলুন, আপনি কোন Shift এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 2nd Shift, 5th Semester)"
            else:
                # Fallback
                clarification_text = "দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন?"
        
        # ============================================================
        # FOR NON-CAPTAIN QUERIES - Use LLM
        # ============================================================
        else:
            # Greetings should feel natural and varied every time, so we use a
            # higher sampling temperature. Clarification / not_possible replies
            # stay more controlled (default temperature).
            llm = get_llm(temperature=0.9) if is_greeting else get_llm()
            chain = _SHORT_INFO_PROMPT | llm

            result = chain.invoke({
                "db_schema": DB_SCHEMA.strip(),
                "failure_reason": failure_reason,
                "user_input": user_input,
                "missing_shift": missing_shift,
                "missing_department": missing_department,
                "missing_semester": missing_semester,
            })

            clarification_text = extract_content(result).strip()

    except Exception as e:
        print(f"[sql_query_short_info_response] LLM error: {e}")
        if is_greeting:
            clarification_text = "হ্যালো! 🎓 আমি CNPIchat, চাঁপাইনবাবগঞ্জ পলিটেকনিক ইন্সটিটিউটের এআই সহকারী। বিভাগ, শিক্ষক, রুটিন — যা জানতে চান বলুন!"
        elif not_possible:
            clarification_text = (
                "দুঃখিত, আপনার প্রশ্নটি আমাদের ডেটাবেজ থেকে উত্তর দেওয়া সম্ভব নয়। "
                "দয়া করে বিভাগ, শিক্ষক, রুটিন বা কলেজ সম্পর্কিত তথ্য জিজ্ঞাসা করুন।"
            )
        else:
            parts = []
            if missing_department:
                parts.append("কোন Department")
            if missing_shift:
                parts.append("কোন Shift")
            if missing_semester:
                parts.append("কোন Semester")
            
            # Add "Class Captain-এর" if this is a captain query
            suffix = "-এর Class Captain-এর তথ্য" if is_captain_query else "-এর তথ্য"
            
            if parts:
                clarification_text = (
                    f"দয়া করে বলুন, আপনি {' এবং '.join(parts)}{suffix} জানতে চাচ্ছেন? "
                    "তাহলে আমি আপনাকে সঠিক উত্তর দিতে পারব।"
                )
            else:
                clarification_text = (
                    "দয়া করে বলুন, আপনি আরও নির্দিষ্ট করে জানান — "
                    "কোন Department, কোন Shift এবং কোন Semester-এর তথ্য জানতে চাচ্ছেন? "
                    "তাহলে আমি আপনাকে সঠিক উত্তর দিতে পারব।"
                )

    return {
        "final_answer": clarification_text,
        "answer_status": answer_status,
        "is_sub_query_call": is_sub_query_call,
        "sql_query": {
            **sql_query_state,
            "final_answer": clarification_text,
        },
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    state_vague = {
        "user_input": "teacher info",
        "is_sub_query_call": False,
        "sql_query": {
            "short_info": True,
            "not_possible": False,
            "final_answer": "",
        },
    }
    result = sql_query_short_info_response_node(state_vague)
    print("final_answer:", result["final_answer"])
