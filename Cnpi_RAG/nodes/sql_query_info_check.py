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
Each department also has multiple semesters.

Shift keywords: morning, 1st, first, day, 2nd, second, shift, মর্নিং, ১ম, প্রথম, ডে, ২য়, দ্বিতীয়, শিফট
Department keywords: CST, ENT, ET, RAC, FT, MT, Computer, Electromedical, Environmental, Refrigeration, Food, Mechanical
Semester keywords: 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, semester, সেমিস্টার, পর্ব, ১ম পর্ব, ৫ম পর্ব

Set "short_info": true IF the query is missing ANY required piece.
For EACH missing piece, set the corresponding flag to true:
- missing_shift: true if the query asks about CI, teachers, or routine (shift-dependent info)
  but does NOT mention which shift.
- missing_department: true if the query asks about department-level info
  but does NOT mention which department.
- missing_semester: true if the query asks about semester-specific info
  but does NOT mention which semester.

Set "short_info": false IF:
- All required info is present, OR
- Query is not shift/department/semester dependent (e.g. principal phone, total students)

CRITICAL — ONLY ask for what is ACTUALLY MISSING:
- If the user already mentioned the department (e.g. "CST") but NOT the shift,
  set missing_shift=true and missing_department=false.
- If the user already mentioned the shift (e.g. "2nd shift") but NOT the department,
  set missing_shift=false and missing_department=true.
- If BOTH shift and department are missing, set both to true.
- NEVER set a missing flag to true if the user already provided that information.
- ONLY ask for the piece(s) that are genuinely absent from the query.

Examples:
User: "CST department er chief instructor ke?"
  -> department=CST is present, shift is missing
  -> missing_shift=true, missing_department=false, missing_semester=false
  -> short_info=true

User: "cst 5th er ci er nam ki"
  -> department=CST is present, semester=5th is present, shift is missing
  -> missing_shift=true, missing_department=false, missing_semester=false
  -> short_info=true

User: "class routine dao"
  -> both department and shift are missing
  -> missing_shift=true, missing_department=true, missing_semester=false
  -> short_info=true

User: "CST Day Shift chief instructor ke?"
  -> department=CST present, shift=Day present
  -> missing_shift=false, missing_department=false, missing_semester=false
  -> short_info=false

User: "Principal phone number"
  -> not shift/department/semester dependent
  -> all flags false, short_info=false

---------------------------------------
HOW TO WRITE THE CLARIFICATION
---------------------------------------
The clarification must ONLY ask for the pieces that are ACTUALLY missing
(as indicated by the missing_* flags). Do NOT ask for information the user
already provided.

Write in Bengali (বাংলা). Keep technical terms (Shift, Department, Semester,
CST, ENT, etc.) in English. Be polite and student-friendly.

GOOD examples:

Only shift missing:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

Only department missing:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

Shift and department both missing:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

Only semester missing:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"
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