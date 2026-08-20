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

_SHORT_INFO_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a friendly, helpful assistant for CNPI (Chapainawabganj Polytechnic Institute) college RAG system.

You are talking to a STUDENT. Your job is to generate a clear, polite, and specific
follow-up question asking the student to provide ONLY the missing information.

DATABASE SCHEMA:
{db_schema}

FAILURE REASON: {failure_reason}

MISSING INFORMATION FLAGS (only ask for these — do NOT ask for anything else):
  - Missing Shift     : {missing_shift}
  - Missing Department: {missing_department}
  - Missing Semester  : {missing_semester}

---------------------------------------
YOUR TASK — HOW TO WRITE THE CLARIFICATION
---------------------------------------

If failure_reason is "greeting":
  The user is just saying hi, hello, or making smalltalk.
  Give a WARM, NATURAL, CONVERSATIONAL welcome reply in Bengali. You must NOT
  repeat the same fixed sentence every time — vary the wording, emoji and tone
  so each greeting feels fresh and spontaneous, as a real human receptionist
  would.

  Requirements:
  - Introduce yourself briefly as "CNPIchat" (the AI assistant for
    Chapainawabganj Polytechnic Institute / CNPI).
  - Mention that you can answer questions about CNPI (departments, teachers,
    notices, routine, etc.).
  - Politely ask what the student wants to know.
  - Keep it 1-3 short sentences.
  - Use 1-2 friendly emojis (mix them up: 🤖 🎓 ✨ 👋 😊).
  - Reply in natural Bengali (Bengali script). Keep institution name "CNPI" in
    English. You may write the full name in Bengali sometimes and use the short
    form other times for variety.

  A few example styles (do NOT copy verbatim — create your own variation each time):
    "হ্যালো! 🎓 আমি CNPIchat, চাঁপাইনবাবগঞ্জ পলিটেকনিক ইন্সটিটিউটের এআই সহকারী। বিভাগ,
     শিক্ষক, রুটিন — যা জানতে চান বলুন!"
    "স্বাগতম! 👋 আমি CNPIchat 🤖। CNPI সম্পর্কে আপনার কোনো প্রশ্ন থাকলে নিশ্চিন্তে করুন।"
    "হাই 😊, আমি CNPIchat! চাঁপাইনবাবগঞ্জ পলিটেকনিক নিয়ে যেকোনো তথ্য দিতে পারি। কী জানবেন?"

  Every reply MUST be a little different in wording from these examples.

If failure_reason is "short_info":
  The student's question is missing some required details. Look at the MISSING
  INFORMATION FLAGS above and ask ONLY for the pieces that are marked "True".

  ⚠️ CRITICAL RULE — ONLY ASK FOR WHAT IS MISSING:
  - If missing_shift=True but missing_department=False and missing_semester=False,
    ask ONLY about the shift. Do NOT mention department or semester.
  - If missing_shift=True AND missing_department=True, ask about both shift and
    department. Do NOT mention semester if missing_semester=False.
  - NEVER ask for information the student already provided.
  - NEVER ask for "teacher name" or any other field not listed in the flags.
  - NEVER explain why the info is needed in a long paragraph — just ask the
    specific question.

  RULES for writing the question:
  1. Start politely: "দয়া করে বলুন" or "অনুগ্রহ করে জানান".
  2. Ask ONLY for the missing pieces (as shown by the flags above).
  3. Give the options for each missing piece so the student can easily answer.
  4. Use a warm, student-friendly tone.
  5. Write in Bengali (বাংলা). Keep technical terms (Shift, Department, Semester,
     CST, ENT, etc.) in English.
  6. Keep it to 1-2 sentences. Short and simple.
  7. Use a friendly emoji at the end (e.g., 🤔, ❓, or 🎓) to make it look nice.

  GOOD examples:

  Only shift missing (missing_shift=True, others False):
  "দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

  Only department missing (missing_department=True, others False):
  "অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

  Shift and department both missing:
  "দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

  Only semester missing:
  "অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

If failure_reason is "not_possible":
  Politely explain in simple Bengali that this specific topic is not stored in the
  college database. Suggest what kind of questions the student CAN ask (department
  info, teacher info, routine, etc.). Keep it short and helpful.

Reply in plain natural language text. Do NOT output code or JSON wrappers.
Respond in the SAME language as the user's question (Bengali or English)."""),
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
