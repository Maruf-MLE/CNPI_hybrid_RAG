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
RULE 2: TIME/DATE/NOTICE Queries — NEVER ask for dept/shift/semester
---------------------------------------
If the query is about TODAY, TOMORROW, or NOTICES, return immediately:
  needs_more_info=false, all missing flags=false

Type A keywords (any match → pass through immediately):
  Banglish: ajke, aajke, aaj, kal, kalke, agamikal, today, tomorrow, yesterday
  Phrases:  class hobe, class hobe na, class ache, class nei, class nai,
            ki hobe, hobe ki, hobe na ki, ki class, class ki
  Notice:   notice, notis, notiish
  Bengali:  আজকে, আজ, কাল, আগামীকাল, ক্লাস হবে, ক্লাস নেই, ক্লাস আছে, নোটিশ

Examples that MUST return needs_more_info=false:
  - "cnpi te ajke ki class hobe"
  - "ajke class ache?"
  - "kal class hobe na?"
  - "today class ache?"
  - "আজকে কি ক্লাস আছে?"
  - "latest notice"

---------------------------------------
RULE 3: Missing Information Check (needs_more_info)
---------------------------------------
ONLY for NON-time queries:

1. ROUTINE/SCHEDULE Queries (need Department + Shift + Semester):
   Keywords: "routine", "schedule", "class routine", "timetable", "ক্লাস রুটিন", "রুটিন"
   - missing_department: true if no dept (CST, ENT, ET, RAC, FT, MT)
   - missing_shift: true if no shift (1st/Morning, 2nd/Day)
   - missing_semester: true if no semester (1st–8th)

2. CI/Teacher Queries (need Department + Shift, NO semester):
   Keywords: "CI", "chief instructor", "teacher", "instructor", "শিক্ষক", "প্রধান"
   - missing_department: true if no dept
   - missing_shift: true if no shift
   - missing_semester: false always

3. General Info (no requirements):
   Keywords: "principal", "phone", "address", "email", "college info", "lab", "history"
   All flags: false

---------------------------------------
RULE 4: GREETINGS & SMALLTALK
---------------------------------------
If query is just greeting/smalltalk (hi, hello, salam, thanks):
  suitable=no, needs_more_info=true, is_greeting=true, all missing flags=false

---------------------------------------
HOW TO WRITE CLARIFICATION
---------------------------------------
Write in Bengali. Keep technical terms in English. Be polite.

Only shift missing:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

Only department missing:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

Only semester missing:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

Dept + Shift missing:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

All three missing:
"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Routine চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"
"""),
    ("human", "User Query: {user_input}")
])


def sql_retrieve_check_node(state: RAGState) -> Dict[str, Any]:
    """Check if query is suitable for semantic search."""

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

    # ================================================================
    # PRE-CHECK: TYPE A — time/date/notice queries bypass LLM entirely
    # These NEVER need department / shift / semester
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
        "notice", "notis", "notiish",
        # Bengali Unicode time words
        "আজকে", "আজ", "কাল", "আগামীকাল", "আগামীকালকে",
        "গতকাল", "পরশু",
        # Bengali class/notice
        "ক্লাস হবে", "ক্লাস নেই", "ক্লাস আছে",
        "নোটিশ", "বিজ্ঞপ্তি",
    ]

    q_lower = user_input.lower()
    if any(kw in q_lower for kw in _TYPE_A_KEYWORDS):
        print(f"[retrieve_check] TYPE A (time/notice) query → skip clarification")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "need_more_info": False,
            }
        }

    # ================================================================
    # LLM CHECK: routine, teacher, general queries
    # ================================================================
    llm = get_llm()
    check_chain = _retrieve_check_prompt | llm.with_structured_output(RetrieveCheckOutput)

    try:
        decision = check_chain.invoke({"user_input": user_input})

        if decision.suitable == "no" or decision.needs_more_info:
            # ============================================================
            # POST-PROCESSING: Generate clarification if LLM didn't provide one
            # ============================================================
            clarification = decision.clarification
            
            # If LLM didn't generate good clarification, create one from flags
            if not clarification or clarification.strip() == "":
                print(f"[retrieve_check] No LLM clarification → generating from flags")
                
                parts = []
                if decision.missing_department:
                    parts.append("কোন Department")
                if decision.missing_shift:
                    parts.append("কোন Shift")
                if decision.missing_semester:
                    parts.append("কোন Semester")
                
                if parts:
                    clarification = (
                        f"দয়া করে বলুন, আপনি {' এবং '.join(parts)}-এর তথ্য জানতে চাচ্ছেন? "
                        "তাহলে আমি আপনাকে সঠিক উত্তর দিতে পারব।"
                    )
                else:
                    clarification = (
                        "দয়া করে বলুন, আপনি আরও নির্দিষ্ট করে জানান — "
                        "কোন Department, কোন Shift এবং কোন Semester-এর তথ্য জানতে চাচ্ছেন? "
                        "তাহলে আমি আপনাকে সঠিক উত্তর দিতে পারব।"
                    )
            
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "need_more_info": True,
                    "final_answer": clarification,
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