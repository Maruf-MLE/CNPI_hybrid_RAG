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
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate


class RetrieveCheckOutput(BaseModel):
    suitable: str = Field(description="yes or no")
    needs_more_info: bool = Field(description="whether information is insufficient")
    clarification: str = Field(description="brief clarification need")
    is_greeting: bool = Field(default=False, description="true if the user is just saying a greeting or smalltalk")
    missing_shift: bool = Field(default=False, description="true if shift is missing and required")
    missing_department: bool = Field(default=False, description="true if department is missing and required")
    missing_semester: bool = Field(default=False, description="true if semester is missing and required")


# System prompt components
CORE_INSTRUCTIONS = """==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are the Retrieve Check Node of a RAG system.

TASK:
Analyze the user's query and determine whether it contains sufficient information for effective retrieval.

Return ONLY valid JSON using this exact schema:

{
  "suitable": "yes" or "no",
  "needs_more_info": boolean,
  "clarification": "brief clarification text",
  "is_greeting": boolean,
  "missing_shift": boolean,
  "missing_department": boolean,
  "missing_semester": boolean
}

DECISION RULES:

RULE 1 — DEFAULT SUITABILITY
Always assume "suitable": "yes" for any project-related question.

RULE 2 — TIME, DATE & NOTICE QUERIES
Never request Department, Shift, or Semester for queries about TODAY, TOMORROW, or NOTICES.

If any Type A keyword or phrase matches:
- Return immediately.
- Set needs_more_info=false.
- Set all missing flags=false.
- Do not ask for clarification.

RULE 3 — MISSING INFORMATION CHECK
Apply this rule ONLY to non-time queries.

A. ROUTINE / SCHEDULE QUERIES
These queries require Department, Shift, and Semester.

Check:
- missing_department = true if no Department is specified.
- missing_shift = true if no Shift is specified.
- missing_semester = true if no Semester is specified.

B. CI / TEACHER QUERIES
These queries require Department and Shift, but NOT Semester.

Check:
- missing_department = true if no Department is specified.
- missing_shift = true if no Shift is specified.
- missing_semester = false always.

C. GENERAL INFORMATION QUERIES
These queries have no additional information requirements.
Set all missing flags=false.

RULE 4 — GREETINGS & SMALLTALK
If the query contains only a greeting or smalltalk:
- suitable = "no"
- needs_more_info = true
- is_greeting = true
- All missing flags = false.

RULE 5 — CLARIFICATION
When information is missing:
- Write clarification in Bengali.
- Keep technical terms in English.
- Use polite and concise language.
- Select the appropriate clarification template from Layer 3.

If no clarification is needed, return an empty string for "clarification".

OUTPUT RESTRICTIONS:
- Return ONLY valid JSON.
- Do not include Markdown, explanations, or text outside JSON.
- Use the exact JSON keys and value types specified above."""

PROJECT_CONFIGURATION = """==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
CNPI RAG System.

DOMAIN:
A Bangladeshi polytechnic institute's academic and institutional information.

DEPARTMENT IDENTIFIERS:
CST, ENT, ET, RAC, FT, MT

SHIFT IDENTIFIERS:
- 1st Shift / Morning
- 2nd Shift / Day

SEMESTER RANGE:
1st–8th Semester

QUERY CATEGORIES:

1. ROUTINE / SCHEDULE:
   routine, schedule, class routine, timetable,
   ক্লাস রুটিন, রুটিন

2. CI / TEACHER:
   CI, chief instructor, teacher, instructor,
   শিক্ষক, প্রধান

3. GENERAL INFORMATION:
   principal, phone, address, email, college info,
   lab, history"""

EXAMPLES_REFERENCE = """==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

A. TIME / DATE / NOTICE KEYWORDS

Banglish:
ajke, aajke, aaj, kal, kalke, agamikal

English:
today, tomorrow, yesterday

Phrases:
class hobe, class hobe na, class ache, class nei,
class nai, ki hobe, hobe ki, hobe na ki,
ki class, class ki

Notice:
notice, notis, notiish

Bengali:
আজকে, আজ, কাল, আগামীকাল, ক্লাস হবে,
ক্লাস নেই, ক্লাস আছে, নোটিশ


B. TIME / DATE / NOTICE EXAMPLES

All examples below MUST return:
needs_more_info=false
All missing flags=false

- "cnpi te ajke ki class hobe"
- "ajke class ache?"
- "kal class hobe na?"
- "today class ache?"
- "আজকে কি ক্লাস আছে?"
- "latest notice"


C. GREETING / SMALLTALK EXAMPLES

Examples:
- hi
- hello
- salam
- thanks

These must follow the greeting rule in Layer 1.


D. CLARIFICATION TEMPLATES

1. ONLY SHIFT MISSING:
"দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

2. ONLY DEPARTMENT MISSING:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর তথ্য চাচ্ছেন? (CST, ENT, ET, RAC, FT, MT)"

3. ONLY SEMESTER MISSING:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর তথ্য জানতে চাচ্ছেন? (1st থেকে 8th পর্যন্ত)"

4. DEPARTMENT + SHIFT MISSING:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

5. ALL THREE MISSING:
"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Routine চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)" """

RETRIEVE_CHECK_SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_REFERENCE}"

_retrieve_check_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=RETRIEVE_CHECK_SYSTEM_PROMPT),
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

    # ================================================================
    # BYPASS LLM: Always return default "suitable" response
    # ================================================================
    print(f"[retrieve_check] Bypassing LLM → returning default suitable response")
    return {
        "sql_retrieve": {
            **sql_retrieve_state,
            "suitable": "yes",
            "needs_more_info": False,
            "clarification": "",
            "is_greeting": False,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": False,
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