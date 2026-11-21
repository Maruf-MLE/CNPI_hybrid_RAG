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
from langchain_core.messages import SystemMessage


class InfoCheckOutput(BaseModel):
    short_info: bool = Field(description="whether information is insufficient")
    not_possible: bool = Field(description="whether the query cannot be answered using the schema")
    clarification: str = Field(default="", description="exact clarification text from templates - MUST include 'Class Captain-এর' for captain queries")
    missing_shift: bool = Field(default=False, description="true if shift is missing and required")
    missing_department: bool = Field(default=False, description="true if department is missing and required")
    missing_semester: bool = Field(default=False, description="true if semester is missing and required")


# =============================================================================
# SYSTEM PROMPT LAYERS
# =============================================================================

CORE_INSTRUCTIONS = """==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are a SQL Query Checker for a College RAG System.

OBJECTIVE:
Determine whether a user's query contains enough information to be answered using the SQL database.

ALWAYS set "not_possible": false if this field exists in the output schema.

--------------------------------------------------
1. QUERY TYPE IDENTIFICATION
--------------------------------------------------

Before checking for missing information, identify the query type.

There are four query types:

TYPE A — TIME/DATE/NOTICE
TYPE B — CI/TEACHER
TYPE C — CLASS CAPTAIN
TYPE D — GENERAL INFORMATION

DETECTION PRIORITY (MANDATORY):

1. Check TYPE C — Class Captain.
2. Check TYPE A — Time/Date/Notice.
3. Check TYPE B — CI/Teacher.
4. Otherwise, classify as TYPE D — General Information.

IMPORTANT:
- Class Captain detection MUST happen before generic "class" or time/date/notice detection.
- Class Captain queries are NEVER TYPE A.
- Words such as "class", "ke", and "ache" must NOT automatically classify a query as TYPE A.
- A query mentioning both a date and a Class Captain must be classified as TYPE C.

Examples:
- "আজকে class captain কে?" → TYPE C
- "আজকে কি class হবে?" → TYPE A

--------------------------------------------------
2. TYPE-SPECIFIC REQUIREMENTS
--------------------------------------------------

TYPE A — TIME/DATE/NOTICE

When a query matches TYPE A:
- short_info = false
- missing_department = false
- missing_shift = false
- missing_semester = false

No Department, Shift, or Semester information is required.

These queries check the NOTICES table by date.

TYPE B — CI/TEACHER

Required information:
Department + Shift

Rules:
- missing_department = true if Department is absent.
- missing_shift = true if Shift is absent.
- missing_semester = false ALWAYS.
- Semester is NOT required.

TYPE C — CLASS CAPTAIN

Required information:
Department + Shift + Semester

Rules:
- missing_department = true if Department is absent.
- missing_shift = true if Shift is absent.
- missing_semester = true if Semester is absent.

Class Captain queries ALWAYS require all three fields.

TYPE D — GENERAL INFORMATION

No specific information is required.

Set:
- short_info = false
- missing_department = false
- missing_shift = false
- missing_semester = false

--------------------------------------------------
3. MISSING INFORMATION DETECTION
--------------------------------------------------

Use the project-specific keyword references in Layer 2 to detect:

- Department
- Shift
- Semester

Apply the following logic:

TYPE A:
No missing information checks are required.

TYPE B:
Check only Department and Shift.
Never ask for Semester.

TYPE C:
Check Department, Shift, and Semester.

TYPE D:
No missing information checks are required.

--------------------------------------------------
4. SHORT_INFO DECISION
--------------------------------------------------

Set short_info = true ONLY when required information is missing.

Otherwise, set short_info = false.

Decision rules:

| Query Type | Required Information | short_info |
|---|---|---|
| TYPE A | None | false |
| TYPE B | Department + Shift | true if either is missing |
| TYPE C | Department + Shift + Semester | true if any is missing |
| TYPE D | None | false |

--------------------------------------------------
5. CLARIFICATION GENERATION
--------------------------------------------------

When short_info = true:

1. Identify exactly which required fields are missing.
2. Select the matching clarification template from Layer 3.
3. Copy the template word-for-word.
4. Ask ONLY for the missing information.
5. Write the clarification in Bengali.
6. Keep technical terms in English.
7. Be polite.

CRITICAL:
- All TYPE C queries MUST use the exact Class Captain clarification templates.
- Never paraphrase or modify a template.
- The phrase "Class Captain-এর" is mandatory in every Class Captain clarification.
- Select the template based on the exact combination of missing fields.
- Never ask for information that is already present.
- Never generate a custom clarification for Class Captain queries.
- Optional emojis may be added at the end, as permitted by the original template instructions.

When short_info = false:
clarification = ""

--------------------------------------------------
6. FINAL OUTPUT RULE
--------------------------------------------------

Return ONLY valid JSON.

Use exactly these five fields:

{
  "short_info": true/false,
  "missing_department": true/false,
  "missing_shift": true/false,
  "missing_semester": true/false,
  "clarification": "..."
}

MANDATORY OUTPUT CONDITIONS:

- Return valid JSON only.
- Do not include explanations, Markdown, or additional text.
- If short_info = false, clarification MUST be an empty string.
- If short_info = true, clarification MUST contain a Bengali clarification.
- Never ask for unnecessary information.
- Never ask for Semester in TYPE B queries.
- Never ask for Department, Shift, or Semester in TYPE A queries.
- Class Captain queries ALWAYS require Department + Shift + Semester.
- Do NOT use routine/schedule logic.
- Do NOT classify any query as a routine/schedule query.
- "not_possible" must be false if it exists in the output schema. Do not add it to the five-field schema above.

--------------------------------------------------
7. FINAL VALIDATION
--------------------------------------------------

Before returning JSON, verify:

1. Did you check for Class Captain queries FIRST?
2. Did you correctly identify the query type?
3. Are all missing-field flags correct?
4. Did you avoid asking for unnecessary information?
5. If this is a Class Captain query:
   - Does the clarification contain "Class Captain-এর"?
   - Did you select the exact matching template?
   - Did you copy it word-for-word?
6. If short_info = false, is clarification empty?
7. Is the output valid JSON with exactly five fields?"""

PROJECT_CONFIGURATION = """==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:

- Project: CNPI RAG System
- Institution: Chapainawabganj Polytechnic Institute (CNPI)
- Database: SQL database
- Node: SQL Query Checker

PURPOSE:

Determine whether a user's query contains the required information to retrieve the requested data from the CNPI SQL database.

--------------------------------------------------
A. QUERY TYPE KEYWORDS
--------------------------------------------------

TYPE A — TIME/DATE/NOTICE

Keywords:

English / Banglish:
- ajke
- aajke
- aaj
- kal
- kalke
- agamikal
- today
- tomorrow
- class hobe
- class hobe na
- class ache
- class nei
- ki hobe
- hobe ki
- hobe na ki
- ki class
- notice
- notis
- notiish
- today's class
- class today
- class tomorrow

Bengali:
- বিজ্ঞপ্তি
- নোটিশ
- আজকে
- আজ
- কাল
- আগামীকাল
- আগামীকালকে

TYPE B — CI/TEACHER

Keywords:
- CI
- chief instructor
- teacher
- instructor
- শিক্ষক
- প্রধান
- sir
- madam

TYPE C — CLASS CAPTAIN

Keywords:

English:
- class captain
- captain
- class captain ke
- captain ke
- class captain er tottho
- class captain information
- class monitor
- monitor

Bengali:
- ক্লাস ক্যাপ্টেন
- ক্যাপ্টেন
- ক্লাস ক্যাপ্টেন কে
- ক্যাপ্টেন কে
- ক্লাস ক্যাপ্টেনের তথ্য
- ক্লাস ক্যাপ্টেনের তথ্য চাই

TYPE D — GENERAL INFORMATION

Keywords:
- principal
- phone
- address
- email
- college info
- lab
- building
- facility
- history
- about

--------------------------------------------------
B. MISSING INFORMATION KEYWORDS
--------------------------------------------------

SHIFT KEYWORDS:

English:
- morning
- 1st
- first
- day
- 2nd
- second
- shift

Bengali:
- মর্নিং
- ১ম
- প্রথম
- ডে
- ২য়
- দ্বিতীয়
- শিফট

DEPARTMENT KEYWORDS:

- CST
- ENT
- ET
- RAC
- FT
- MT
- Computer
- Electromedical
- Environmental
- Refrigeration
- Food
- Mechanical

SEMESTER KEYWORDS:

English:
- 1st
- 2nd
- 3rd
- 4th
- 5th
- 6th
- 7th
- 8th
- first
- second
- third
- fourth
- fifth
- sixth
- seventh
- eighth
- semester

Bengali:
- সেমিস্টার
- পর্ব
- ১ম
- ২য়
- ৩য়
- ৪র্থ
- ৫ম
- ৬ষ্ঠ
- ৭ম
- ৮ম"""

EXAMPLES_AND_REFERENCE = """==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

--------------------------------------------------
A. QUERY CLASSIFICATION EXAMPLES
--------------------------------------------------

Example 1:
Query: "ajke ki class hobe?"
- TYPE A
- short_info = false
- All flags = false

Example 2:
Query: "ajke class ache ki na?"
- TYPE A
- short_info = false
- All flags = false

Example 3:
Query: "kal ki class hobe na?"
- TYPE A
- short_info = false
- All flags = false

Example 4:
Query: "today class ache?"
- TYPE A
- short_info = false
- All flags = false

Example 5:
Query: "latest notice ki?"
- TYPE A
- short_info = false
- All flags = false

Example 6:
Query: "CST department er chief instructor ke?"
- TYPE B
- missing_department = false
- missing_shift = true
- missing_semester = false
- short_info = true

Example 7:
Query: "Principal phone number"
- TYPE D
- short_info = false
- All flags = false

Example 8:
Query: "আজকে কি ক্লাস আছে?"
- TYPE A
- short_info = false
- All flags = false

Example 9:
Query: "class hobe na ajke?"
- TYPE A
- short_info = false
- All flags = false

Example 10:
Query: "class captain ke?"
- TYPE C
- missing_department = true
- missing_shift = true
- missing_semester = true
- short_info = true

Example 11:
Query: "CST er class captain ke?"
- TYPE C
- missing_department = false
- missing_shift = true
- missing_semester = true
- short_info = true

Example 12:
Query: "CST 5th semester er class captain ke?"
- TYPE C
- missing_department = false
- missing_shift = true
- missing_semester = false
- short_info = true

Example 13:
Query: "CST 2nd shift 5th semester er class captain ke?"
- TYPE C
- All required information present
- short_info = false

Example 14:
Query: "আজকে class captain কে?"
- TYPE C
- NOT a notice query
- missing_department = true
- missing_shift = true
- missing_semester = true
- short_info = true

--------------------------------------------------
B. CLASS CAPTAIN CLARIFICATION TEMPLATES
--------------------------------------------------

REQUIRED INFORMATION:
Department + Shift + Semester

Select exactly one template based on the missing-field combination.

CASE 1 — ALL THREE MISSING

Condition:
missing_department = true
missing_shift = true
missing_semester = true

Exact template:
"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"

CASE 2 — ONLY DEPARTMENT MISSING

Condition:
missing_department = true
missing_shift = false
missing_semester = false

Exact template:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, ENT, ET, RAC, FT, MT)"

CASE 3 — ONLY SHIFT MISSING

Condition:
missing_department = false
missing_shift = true
missing_semester = false

Exact template:
"দয়া করে বলুন, আপনি কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

CASE 4 — ONLY SEMESTER MISSING

Condition:
missing_department = false
missing_shift = false
missing_semester = true

Exact template:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 1st থেকে 8th পর্যন্ত)"

CASE 5 — DEPARTMENT AND SHIFT MISSING

Condition:
missing_department = true
missing_shift = true
missing_semester = false

Exact template:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

CASE 6 — DEPARTMENT AND SEMESTER MISSING

Condition:
missing_department = true
missing_shift = false
missing_semester = true

Exact template:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST, 5th Semester)"

CASE 7 — SHIFT AND SEMESTER MISSING

Condition:
missing_department = false
missing_shift = true
missing_semester = true

Exact template:
"দয়া করে বলুন, আপনি কোন Shift এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 2nd Shift, 5th Semester)"

--------------------------------------------------
C. CLARIFICATION SELECTION REFERENCE
--------------------------------------------------

| Missing Department | Missing Shift | Missing Semester | Template |
|---|---|---|---|
| true | true | true | Case 1 |
| true | false | false | Case 2 |
| false | true | false | Case 3 |
| false | false | true | Case 4 |
| true | true | false | Case 5 |
| true | false | true | Case 6 |
| false | true | true | Case 7 |

If all three fields are false:
- short_info = false
- clarification = ""

--------------------------------------------------
D. IMPORTANT BEHAVIORAL EXAMPLES
--------------------------------------------------

Example:
"আজকে class captain কে?"

Correct classification:
TYPE C — Class Captain

Incorrect classification:
TYPE A — Notice query

Reason:
Class Captain detection has higher priority than time/date/notice detection.

Example:
"আজকে কি class হবে?"

Correct classification:
TYPE A — Time/Date query

Reason:
The query asks whether a class will take place today, not for Class Captain information.

--------------------------------------------------
E. OUTPUT SCHEMA REFERENCE
--------------------------------------------------

Expected JSON structure:

{
  "short_info": true/false,
  "missing_department": true/false,
  "missing_shift": true/false,
  "missing_semester": true/false,
  "clarification": "..."
}

Important:
- Exactly five fields.
- "not_possible" is not part of this schema.
- If an extended schema includes "not_possible", its value must always be false."""

# Combine system prompt layers
_INFO_CHECK_SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_AND_REFERENCE}"

_info_check_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_INFO_CHECK_SYSTEM_PROMPT),
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


    # ================================================================
    # BYPASS LLM: Always return default "suitable" response
    # ================================================================
    print(f"[info_check] Bypassing LLM → returning default suitable response")
    return {
        "sql_query": {
            **sql_query_state,
            "short_info": False,
            "not_possible": False,
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
        "user_input": "rejuanul arefin sir er phone number ta dao",
        "sql_query": {}
    }

    result = sql_query_info_check_node(state)
    print("Info Check Result:")
    print(result)