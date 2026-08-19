"""
SQL Query Info Check Node - Phase 2
===================================

Analyze query to determine if it's answerable via SQL and if it has sufficient detail.

Flow: user_input + sql_query → sql_query.short_info / sql_query.not_possible
"""

import sys
from pathlib import Path

from pydantic import BaseModel, Field

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm
from langchain_core.prompts import ChatPromptTemplate


class InfoCheckOutput(BaseModel):
    short_info: bool = Field(description="whether information is insufficient")
    not_possible: bool = Field(description="whether the query cannot be answered using the schema")
    clarification: str = Field(default="", description="brief clarification needed")
    missing_shift: bool = Field(default=False, description="true if shift is missing and required")
    missing_department: bool = Field(default=False, description="true if department is missing and required")
    missing_semester: bool = Field(default=False, description="true if semester is missing and required")


_INFO_CHECK_SYSTEM_PROMPT = """You are a SQL Query Checker for CNPI RAG System.

Your job: Check if the user query has enough information to be answered from the SQL database.

ALWAYS set "not_possible": false.

=======================================
QUERY TYPE IDENTIFICATION (DO THIS FIRST)
=======================================

Before checking for missing info, identify the query type:

TYPE A — TIME/DATE/NOTICE Queries (NEVER ask for dept/shift/semester):
  Keywords: "ajke", "aajke", "aaj", "kal", "kalke", "agamikal", "today", "tomorrow",
            "class hobe", "class hobe na", "class ache", "class nei",
            "ki hobe", "hobe ki", "hobe na ki", "ki class",
            "notice", "notis", "notiish", "বিজ্ঞপ্তি", "নোটিশ",
            "today's class", "class today", "class tomorrow",
            "আজকে", "আজ", "কাল", "আগামীকাল", "আগামীকালকে"
  
  RULE: If query contains ANY of these keywords → short_info=false, all flags=false
  REASON: These queries check NOTICES table by date — no dept/shift/semester needed.
  
  Examples that MUST return short_info=false:
  - "ajke ki class hobe?"
  - "ajke class ache?"
  - "kal class hobe na?"
  - "today class ache?"
  - "agamikal ki hobe?"
  - "class hobe ki na ajke?"
  - "আজকে কি ক্লাস আছে?"
  - "কাল কি ক্লাস হবে?"
  - "latest notice"
  - "শেষ নোটিশ"

TYPE B — ROUTINE/SCHEDULE Queries (need Department + Shift + Semester):
  Keywords: "routine", "schedule", "class routine", "timetable",
            "ক্লাস রুটিন", "রুটিন", "সময়সূচী"
  
  NOTE: "routine" queries are DIFFERENT from "class hobe ki na" queries.
  "class hobe ki na" = checking notice, NOT asking for routine.
  
  MANDATORY CHECKS:
  - missing_department: true if no department mentioned (CST, ENT, ET, RAC, FT, MT)
  - missing_shift: true if no shift mentioned (1st/Morning, 2nd/Day)
  - missing_semester: true if no semester mentioned (1st through 8th)

TYPE C — CI/Teacher Queries (need Department + Shift, NO semester):
  Keywords: "CI", "chief instructor", "teacher", "instructor",
            "শিক্ষক", "প্রধান", "sir", "madam"
  
  MANDATORY CHECKS:
  - missing_department: true if no department mentioned
  - missing_shift: true if no shift mentioned
  - missing_semester: false (semester NOT needed)

TYPE D — General Info Queries (no specific requirements):
  Keywords: "principal", "phone", "address", "email", "college info",
            "lab", "building", "facility", "history", "about"
  All flags: false

=======================================
DETECTION PRIORITY ORDER
=======================================

1. First check if it is TYPE A (time/date/notice) → if yes, STOP → return all false
2. Then check if TYPE B (routine) → apply routine rules
3. Then check if TYPE C (teacher/CI) → apply teacher rules
4. Otherwise TYPE D → all false

=======================================
MISSING INFORMATION CHECK (Type B and C only)
=======================================

Shift keywords: morning, 1st, first, day, 2nd, second, shift, মর্নিং, ১ম, প্রথম, ডে, ২য়, দ্বিতীয়, শিফট
Department keywords: CST, ENT, ET, RAC, FT, MT, Computer, Electromedical, Environmental, Refrigeration, Food, Mechanical
Semester keywords: 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, semester, সেমিস্টার, পর্ব

=======================================
EXAMPLES WITH ANALYSIS
=======================================

Example 1: "ajke ki class hobe?"
→ TYPE A (contains "ajke" + "class hobe")
→ short_info=false, all flags=false ✅

Example 2: "ajke class ache ki na?"
→ TYPE A (contains "ajke" + "class")
→ short_info=false, all flags=false ✅

Example 3: "kal ki class hobe na?"
→ TYPE A (contains "kal" + "class hobe")
→ short_info=false, all flags=false ✅

Example 4: "today class ache?"
→ TYPE A (contains "today" + "class")
→ short_info=false, all flags=false ✅

Example 5: "latest notice ki?"
→ TYPE A (contains "notice")
→ short_info=false, all flags=false ✅

Example 6: "class routine dao"
→ TYPE B (contains "routine")
→ missing_department=true, missing_shift=true, missing_semester=true
→ short_info=true ✅

Example 7: "CST Day Shift 5th semester routine"
→ TYPE B (routine with all info)
→ short_info=false ✅

Example 8: "CST department er chief instructor ke?"
→ TYPE C (teacher/CI query, has dept but no shift)
→ missing_shift=true → short_info=true ✅

Example 9: "Principal phone number"
→ TYPE D (general info)
→ short_info=false ✅

Example 10: "আজকে কি ক্লাস আছে?"
→ TYPE A (Bengali: আজকে + ক্লাস আছে)
→ short_info=false, all flags=false ✅

Example 11: "class hobe na ajke?"
→ TYPE A (contains "class hobe" + "ajke")
→ short_info=false, all flags=false ✅

=======================================
HOW TO WRITE THE CLARIFICATION
=======================================
You MUST fill the "clarification" field whenever short_info is true.

The clarification must ONLY ask for the pieces that are ACTUALLY missing.
Write in Bengali (বাংলা). Keep technical terms in English. Be polite.

Only shift missing:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

Only department missing:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

Only semester missing:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

Shift and department both missing:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

All three missing (routine query):
"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Routine চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"
"""

_info_check_prompt = ChatPromptTemplate.from_messages([
    ("system", _INFO_CHECK_SYSTEM_PROMPT),
    ("human", "User Query: {user_input}\n\nSTEP 1: Is this a TYPE A query (time/date/notice)? Check for: ajke, kal, today, tomorrow, class hobe, hobe na, notice\nSTEP 2: If TYPE A → return short_info=false, all flags=false\nSTEP 3: If not TYPE A → check TYPE B/C/D rules"),
])


def sql_query_info_check_node(state: RAGState) -> dict:
    """Check if SQL query can be answered and has sufficient detail."""

    user_input = state.get("normalized_query") or state.get("user_input", "")
    sql_query_state = state.get("sql_query", {})

    if not user_input:
        return {
            "sql_query": {
                **sql_query_state,
                "short_info": True,
                "final_answer": "দয়া করে আপনার প্রশ্নটি লিখুন।",
            }
        }

    # ================================================================
    # PRE-CHECK: TYPE A queries (time/date/notice) bypass LLM entirely
    # These NEVER need department/shift/semester
    # ================================================================
    _TYPE_A_KEYWORDS = [
        # Banglish time words
        "ajke", "aajke", "aaj", "kal", "kalke", "agamikal", "agamikaal",
        "parsu", "gotokal",
        # English time words
        "today", "tomorrow", "yesterday",
        # Class status phrases
        "class hobe", "class hobe na", "class ache", "class nei",
        "class nai", "ki class", "class ki",
        "hobe ki na", "hobe na ki", "ki hobe",
        # Notice keywords
        "notice", "notis", "notiish", "latest notice",
        # Bengali Unicode time words
        "আজকে", "আজ", "কাল", "আগামীকাল", "আগামীকালকে",
        "গতকাল", "পরশু",
        # Bengali class status
        "ক্লাস হবে", "ক্লাস নেই", "ক্লাস আছে",
        "নোটিশ", "বিজ্ঞপ্তি",
    ]

    q_lower = user_input.lower()
    is_type_a = any(kw in q_lower for kw in _TYPE_A_KEYWORDS)

    if is_type_a:
        print(f"[info_check] TYPE A (time/notice) query detected → skip clarification")
        return {
            "sql_query": {
                **sql_query_state,
                "short_info": False,
                "not_possible": False,
            }
        }

    # ================================================================
    # LLM CHECK: For routine, teacher, and other queries
    # ================================================================
    llm = get_llm()
    info_check_chain = _info_check_prompt | llm.with_structured_output(InfoCheckOutput)

    try:
        decision = info_check_chain.invoke({"user_input": user_input})

        if decision.short_info:
            return {
                "sql_query": {
                    **sql_query_state,
                    "short_info": True,
                    "final_answer": decision.clarification,
                    "missing_shift": decision.missing_shift,
                    "missing_department": decision.missing_department,
                    "missing_semester": decision.missing_semester,
                }
            }
        elif decision.not_possible:
            return {
                "sql_query": {
                    **sql_query_state,
                    "not_possible": True,
                    "final_answer": (
                        "দুঃখিত, এই তথ্যটি আমাদের ডেটাবেজে সংরক্ষিত নেই। "
                        "দয়া করে বিভাগ, শিক্ষক, বা কলেজ সম্পর্কিত তথ্য জিজ্ঞাসা করুন।"
                    ),
                }
            }
        else:
            return {
                "sql_query": {
                    **sql_query_state,
                    "short_info": False,
                    "not_possible": False,
                }
            }
    except Exception as e:
        print(f"Info check error: {e}")
        return {
            "sql_query": {
                **sql_query_state,
                "short_info": False,
                "not_possible": False,
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "user_input": "rejuanul arefin sir er phone number ta dao",
        "sql_query": {}
    }

    result = sql_query_info_check_node(state)
    print("Info Check Result:")
    print(result)