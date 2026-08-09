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

---------------------------------------
MISSING INFORMATION CHECK
---------------------------------------
CNPI has 6 departments with 2 shifts each: Morning/1st and Day/2nd.
Each shift has different CI, teachers, and routines.
Each department also has multiple semesters (1st to 8th).

Shift keywords: morning, 1st, first, day, 2nd, second, shift, মর্নিং, ১ম, প্রথম, ডে, ২য়, দ্বিতীয়, শিফট
Department keywords: CST, ENT, ET, RAC, FT, MT, Computer, Electromedical, Environmental, Refrigeration, Food, Mechanical
Semester keywords: 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, semester, সেমিস্টার, পর্ব, ১ম পর্ব, ৫ম পর্ব

CRITICAL DETECTION RULES:
==========================

1. ROUTINE/SCHEDULE Queries (ALWAYS need Department + Shift + Semester):
   Keywords: "routine", "schedule", "class routine", "timetable", "ক্লাস রুটিন", "রুটিন"
   
   MANDATORY CHECKS when these keywords are present:
   - missing_department: true if no department mentioned (CST, ENT, ET, RAC, FT, MT)
   - missing_shift: true if no shift mentioned (1st/Morning, 2nd/Day)
   - missing_semester: true if no semester mentioned (1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th)
   
   Even if the user mentions department and shift, you MUST check if semester is missing.
   ROUTINE QUERIES ARE INCOMPLETE WITHOUT SEMESTER.

2. CI/Teacher Queries (need Department + Shift, NO semester):
   Keywords: "CI", "chief instructor", "teacher", "instructor", "শিক্ষক", "প্রধান"
   
   Checks:
   - missing_department: true if no department mentioned
   - missing_shift: true if no shift mentioned
   - missing_semester: false (semester NOT needed for CI/teacher queries)

3. General Info Queries (no specific requirements):
   Keywords: "principal", "phone", "address", "email", "college info"
   All flags: false

Set "short_info": true IF the query is missing ANY required piece based on the rules above.
Set "short_info": false IF all required information is present.

STEP-BY-STEP ANALYSIS:
======================
1. First, identify the query type (routine vs CI/teacher vs general)
2. Then check which pieces are PRESENT in the query
3. Finally, set missing_* flags for pieces that are REQUIRED but NOT PRESENT

Examples with Step-by-Step Analysis:
======================================

Example 1: "Where can I find the class Routine for the CST Department Day Shift?"
Step 1: Query type = ROUTINE (keyword: "Routine")
Step 2: Check what's present:
  - Department = CST ✓ (present)
  - Shift = Day ✓ (present)
  - Semester = ✗ (NOT present)
Step 3: Set flags:
  -> ROUTINE queries need Department + Shift + Semester
  -> Department present, so missing_department=false
  -> Shift present, so missing_shift=false
  -> Semester NOT present, so missing_semester=true
  -> short_info=true (because semester is missing)

Example 2: "CST Day Shift 5th semester routine"
Step 1: Query type = ROUTINE
Step 2: Check what's present:
  - Department = CST ✓
  - Shift = Day ✓
  - Semester = 5th ✓
Step 3: All required info present
  -> missing_shift=false, missing_department=false, missing_semester=false
  -> short_info=false

Example 3: "class routine dao"
Step 1: Query type = ROUTINE
Step 2: Check what's present:
  - Department = ✗
  - Shift = ✗
  - Semester = ✗
Step 3: All three required pieces missing
  -> missing_shift=true, missing_department=true, missing_semester=true
  -> short_info=true

Example 4: "CST Day Shift chief instructor ke?"
Step 1: Query type = CI/TEACHER (keyword: "chief instructor")
Step 2: Check what's present:
  - Department = CST ✓
  - Shift = Day ✓
  - Semester = not needed for CI queries
Step 3: All required info present (semester not needed)
  -> missing_shift=false, missing_department=false, missing_semester=false
  -> short_info=false

Example 5: "CST department er chief instructor ke?"
Step 1: Query type = CI/TEACHER
Step 2: Check what's present:
  - Department = CST ✓
  - Shift = ✗
Step 3: Shift is missing but required for CI queries
  -> missing_shift=true, missing_department=false, missing_semester=false
  -> short_info=true

Example 6: "Principal phone number"
Step 1: Query type = GENERAL INFO (not department/shift/semester dependent)
Step 2: No specific info needed
Step 3: All flags false
  -> missing_shift=false, missing_department=false, missing_semester=false
  -> short_info=false

---------------------------------------
HOW TO WRITE THE CLARIFICATION
---------------------------------------
You MUST fill the "clarification" field whenever short_info is true.

The clarification must ONLY ask for the pieces that are ACTUALLY missing
(as indicated by the missing_* flags). Do NOT ask for information the user
already provided.

Write in Bengali (বাংলা). Keep technical terms (Shift, Department, Semester,
CST, ENT, etc.) in English. Be polite and student-friendly.

IMPORTANT: Match the clarification to the missing_* flags:
- If only missing_shift is true, ask ONLY for shift
- If only missing_department is true, ask ONLY for department
- If only missing_semester is true, ask ONLY for semester
- If multiple flags are true, ask for ALL of them in ONE sentence

GOOD examples:

Only shift missing:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

Only department missing:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

Only semester missing:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

Shift and department both missing (semester not needed):
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

Shift and semester both missing (but department present):
"দয়া করে বলুন, আপনি কোন Shift এবং কোন Semester-এর তথ্য জানতে চাচ্ছেন? (যেমন: 1st Shift, 5th Semester)"

Department and semester both missing (but shift present):
"দয়া করে বলুন, আপনি কোন Department এবং কোন Semester-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 5th Semester)"

Department, shift, and semester all missing (e.g., "class routine dao"):
"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Routine চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"
"""

_info_check_prompt = ChatPromptTemplate.from_messages([
    ("system", _INFO_CHECK_SYSTEM_PROMPT),
    ("human", "User Query: {user_input}"),
])


def sql_query_info_check_node(state: RAGState) -> dict:
    """Check if SQL query can be answered and has sufficient detail."""
    llm = get_llm()
    info_check_chain = _info_check_prompt | llm.with_structured_output(InfoCheckOutput)

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