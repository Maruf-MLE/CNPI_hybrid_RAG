"""
SQL Retrieve Check Node - Phase 3
================================

Analyze query to determine if it's suitable for semantic retrieval and 
has sufficient information.

Flow: user_input + sql_retrieve -> sql_retrieve.need_more_info / path decision
"""

import sys
from pathlib import Path
from typing import Dict, Any

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


class RetrieveCheckOutput(BaseModel):
    suitable: str = Field(description="yes or no")
    needs_more_info: bool = Field(description="whether information is insufficient")
    clarification: str = Field(description="brief clarification need")
    is_greeting: bool = Field(default=False, description="true if the user is just saying a greeting or smalltalk")
    missing_shift: bool = Field(default=False, description="true if shift is missing and required")
    missing_department: bool = Field(default=False, description="true if department is missing and required")
    missing_semester: bool = Field(default=False, description="true if semester is missing and required")


_retrieve_check_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Retrieve Check Node for the CNPI RAG System.

Analyze the user query to determine if it has sufficient information to be effectively searched.

Return JSON with:
{{
  "suitable": "yes" or "no",
  "needs_more_info": boolean,
  "clarification": "brief clarification text",
  "is_greeting": boolean,
  "missing_shift": boolean,
  "missing_department": boolean,
  "missing_semester": boolean
}}

---------------------------------------
RULE 1: Default suitable
---------------------------------------
Always assume "suitable": "yes" for any college-related question.

---------------------------------------
RULE 2: Missing Information Check (needs_more_info)
---------------------------------------
CNPI has 6 departments, EACH with 2 shifts:
1. Morning / First / 1st shift
2. Day / Second / 2nd shift

Each shift has different Chief Instructors, teachers, and routines.
Each department also has multiple semesters.

You MUST set "needs_more_info": true if the query is missing ANY required piece.
For EACH missing piece, set the corresponding flag to true:
- missing_shift: true if the query asks about CI, teachers, or routine (shift-dependent)
  but does NOT mention which shift.
- missing_department: true if the query asks about department-level info
  but does NOT mention which department.
- missing_semester: true if the query asks about semester-specific info
  but does NOT mention which semester.

If the user already provided a piece of information, set the corresponding flag to
FALSE. NEVER set a missing flag to true if the user already provided that info.

CRITICAL — ONLY ask for what is ACTUALLY MISSING:
- If user already mentioned department (e.g. "CST") but NOT shift:
  missing_shift=true, missing_department=false, missing_semester=false
- If user already mentioned shift (e.g. "2nd shift") but NOT department:
  missing_shift=false, missing_department=true
- If BOTH shift and department are missing: set both to true.

Examples:
User: "CST department er chief instructor ke?"
  -> missing_shift=true, missing_department=false, missing_semester=false
User: "cst 5th er ci er nam ki"
  -> missing_shift=true, missing_department=false, missing_semester=false
User: "class routine dao"
  -> missing_shift=true, missing_department=true, missing_semester=false

If the user ALREADY mentions all required info, set "needs_more_info": false,
all missing flags to false, and leave clarification empty.

---------------------------------------
HOW TO WRITE THE CLARIFICATION
---------------------------------------
The clarification must ONLY ask for the pieces that are ACTUALLY missing.
Do NOT ask for information the user already provided.
Do NOT ask for "teacher name" or anything not in the missing flags.

Write in Bengali (বাংলা). Keep technical terms in English. Be polite and student-friendly.

GOOD examples:

Only shift missing:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

Only department missing:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

Shift and department both missing:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

Only semester missing:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

---------------------------------------
RULE 3: GREETINGS & SMALLTALK
---------------------------------------
If the user's query is just a greeting or smalltalk (e.g., "hi", "hello", "hey", "salam", "kemon asen", "thanks"):
- Set "suitable": "no"
- Set "needs_more_info": true
- Set "is_greeting": true
- All missing flags MUST be false.
"""),
    ("human", "User Query: {user_input}")
])


def sql_retrieve_check_node(state: RAGState) -> Dict[str, Any]:
    """Check if query is suitable for semantic search."""
    llm = get_llm()
    check_chain = _retrieve_check_prompt | llm.with_structured_output(RetrieveCheckOutput)

    user_input = state.get("normalized_query") or state.get("user_input", "")
    sql_retrieve_state = state.get("sql_retrieve", {})

    if not user_input:
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "need_more_info": True,
                "final_answer": "দয়া করে আপনার প্রশ্নটি লিখুন।",
            }
        }

    try:
        decision = check_chain.invoke({"user_input": user_input})

        if decision.suitable == "no" or decision.needs_more_info:
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "need_more_info": True,
                    "final_answer": decision.clarification,
                },
                "sql_query": {
                    "short_info": True,
                    "is_greeting": getattr(decision, "is_greeting", False),
                    "missing_shift": decision.missing_shift,
                    "missing_department": decision.missing_department,
                    "missing_semester": decision.missing_semester,
                },
            }
        else:
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "need_more_info": False,
                }
            }
    except Exception as e:
        print(f"Retrieve check error: {e}")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "need_more_info": True,
                "final_answer": (
                    "দয়া করে বলুন, আপনি আরও নির্দিষ্ট করে জানান — "
                    "কোন Department, কোন Shift এবং কোন Semester-এর তথ্য জানতে চাচ্ছেন? "
                    "তাহলে আমি আপনাকে সঠিক উত্তর দিতে পারব।"
                ),
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "user_input": "Tell me about the history of NCPI",
        "sql_retrieve": {}
    }

    result = sql_retrieve_check_node(state)
    print("Retrieve Check Result:")
    print(result)