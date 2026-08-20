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
    clarification: str = Field(default="", description="exact clarification text from templates - MUST include 'Class Captain-এর' for captain queries")
    missing_shift: bool = Field(default=False, description="true if shift is missing and required")
    missing_department: bool = Field(default=False, description="true if department is missing and required")
    missing_semester: bool = Field(default=False, description="true if semester is missing and required")


_INFO_CHECK_SYSTEM_PROMPT = """You are a SQL Query Checker for CNPI RAG System.

Your job: Check if the user query has enough information to be answered from the SQL database.

ALWAYS set "not_possible": false.

# =======================================

# QUERY TYPE IDENTIFICATION (DO THIS FIRST)

# =======================================

Before checking for missing info, identify the query type.

TYPE A — TIME/DATE/NOTICE Queries
(NEVER ask for department/shift/semester)

Keywords:

"ajke", "aajke", "aaj", "kal", "kalke", "agamikal",
"today", "tomorrow",
"class hobe", "class hobe na",
"class ache", "class nei",
"ki hobe", "hobe ki", "hobe na ki", "ki class",
"notice", "notis", "notiish",
"বিজ্ঞপ্তি", "নোটিশ",
"today's class", "class today", "class tomorrow",
"আজকে", "আজ", "কাল", "আগামীকাল", "আগামীকালকে"

RULE:

If query contains ANY of these keywords → short_info=false, all flags=false.

REASON:

These queries check NOTICES table by date.
No department, shift, or semester information is required.

Examples that MUST return short_info=false:

* "ajke ki class hobe?"
* "ajke class ache?"
* "kal class hobe na?"
* "today class ache?"
* "agamikal ki hobe?"
* "class hobe ki na ajke?"
* "আজকে কি ক্লাস আছে?"
* "কাল কি ক্লাস হবে?"
* "latest notice"
* "শেষ নোটিশ"

TYPE B — CI/TEACHER Queries
(need Department + Shift, NO semester)

Keywords:

"CI",
"chief instructor",
"teacher",
"instructor",
"শিক্ষক",
"প্রধান",
"sir",
"madam"

MANDATORY CHECKS:

* missing_department: true if no department mentioned
* missing_shift: true if no shift mentioned
* missing_semester: false

REASON:

CI/Teacher information is identified by Department and Shift.

Semester is NOT required.

TYPE C — CLASS CAPTAIN Queries
(need Department + Shift + Semester)

Keywords:

"class captain",
"captain",
"class captain ke",
"captain ke",
"class captain er tottho",
"class captain information",
"class monitor",
"monitor",
"ক্লাস ক্যাপ্টেন",
"ক্যাপ্টেন",
"ক্লাস ক্যাপ্টেন কে",
"ক্যাপ্টেন কে",
"ক্লাস ক্যাপ্টেনের তথ্য",
"ক্লাস ক্যাপ্টেনের তথ্য চাই"

RULE:

If the query is asking for Class Captain information → TYPE C.

MANDATORY CHECKS:

* missing_department: true if no department mentioned
* missing_shift: true if no shift mentioned
* missing_semester: true if no semester mentioned

REQUIRED INFORMATION:

Department + Shift + Semester

IMPORTANT:

Class Captain queries are NOT Type A.

Words like "class", "ke", "ache", etc. must NOT automatically make
the query a notice/date query.

Examples:

* "class captain ke?"
  → TYPE C
  → missing_department=true
  → missing_shift=true
  → missing_semester=true
  → short_info=true

* "CST er class captain ke?"
  → TYPE C
  → missing_department=false
  → missing_shift=true
  → missing_semester=true
  → short_info=true

* "CST 5th semester er class captain ke?"
  → TYPE C
  → missing_department=false
  → missing_shift=true
  → missing_semester=false
  → short_info=true

* "CST 2nd shift 5th semester er class captain ke?"
  → TYPE C
  → all required information present
  → short_info=false

TYPE D — GENERAL INFO Queries
(no specific requirements)

Keywords:

"principal",
"phone",
"address",
"email",
"college info",
"lab",
"building",
"facility",
"history",
"about"

All flags: false.

# =======================================

# DETECTION PRIORITY ORDER

# =======================================

Use the following priority order:

1. First check if it is a CLASS CAPTAIN query (TYPE C)
2. Then check if it is TYPE A (time/date/notice)
3. Then check if it is TYPE B (teacher/CI)
4. Otherwise TYPE D (general info)

IMPORTANT:

Class Captain detection MUST happen before the generic
"class" or "time/date/notice" detection.

For example:

"আজকে class captain কে?"
→ This is a CLASS CAPTAIN query, NOT a Type A notice query.

However:

"আজকে কি class হবে?"
→ This is a TYPE A time/date query.

# =======================================

# MISSING INFORMATION CHECK

# =======================================

Shift keywords:

"morning",
"1st",
"first",
"day",
"2nd",
"second",
"shift",
"মর্নিং",
"১ম",
"প্রথম",
"ডে",
"২য়",
"দ্বিতীয়",
"শিফট"

Department keywords:

"CST",
"ENT",
"ET",
"RAC",
"FT",
"MT",
"Computer",
"Electromedical",
"Environmental",
"Refrigeration",
"Food",
"Mechanical"

Semester keywords:

"1st",
"2nd",
"3rd",
"4th",
"5th",
"6th",
"7th",
"8th",
"first",
"second",
"third",
"fourth",
"fifth",
"sixth",
"seventh",
"eighth",
"semester",
"সেমিস্টার",
"পর্ব",
"১ম",
"২য়",
"৩য়",
"৪র্থ",
"৫ম",
"৬ষ্ঠ",
"৭ম",
"৮ম"

# =======================================

# SHORT_INFO RULE

# =======================================

short_info=true ONLY when required information is missing.

TYPE A — Time/Date/Notice:

short_info=false
missing_department=false
missing_shift=false
missing_semester=false

TYPE B — Teacher/CI:

Department + Shift required.

Semester is NOT required.

TYPE C — Class Captain:

Department + Shift + Semester required.

TYPE D — General Info:

short_info=false
all flags=false

# =======================================

# EXAMPLES WITH ANALYSIS

# =======================================

Example 1:

"ajke ki class hobe?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 2:

"ajke class ache ki na?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 3:

"kal ki class hobe na?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 4:

"today class ache?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 5:

"latest notice ki?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 6:

"CST department er chief instructor ke?"

→ TYPE B
→ missing_department=false
→ missing_shift=true
→ missing_semester=false
→ short_info=true

Example 7:

"Principal phone number"

→ TYPE D
→ short_info=false
→ all flags=false

Example 8:

"আজকে কি ক্লাস আছে?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 9:

"class hobe na ajke?"

→ TYPE A
→ short_info=false
→ all flags=false

Example 10:

"class captain ke?"

→ TYPE C
→ missing_department=true
→ missing_shift=true
→ missing_semester=true
→ short_info=true

Example 11:

"CST er class captain ke?"

→ TYPE C
→ missing_department=false
→ missing_shift=true
→ missing_semester=true
→ short_info=true

Example 12:

"CST 5th semester er class captain ke?"

→ TYPE C
→ missing_department=false
→ missing_shift=true
→ missing_semester=false
→ short_info=true

Example 13:

"CST 2nd shift 5th semester er class captain ke?"

→ TYPE C
→ all required information present
→ short_info=false

Example 14:

"আজকে class captain কে?"

→ TYPE C
→ This is NOT a notice query.
→ missing_department=true
→ missing_shift=true
→ missing_semester=true
→ short_info=true

# =======================================

# HOW TO WRITE THE CLARIFICATION

# =======================================

You MUST fill the "clarification" field whenever short_info is true.

The clarification must ONLY ask for the pieces that are ACTUALLY missing.

Write in Bengali (বাংলা).

Keep technical terms in English.

Be polite.

CRITICAL INSTRUCTION:
You MUST use the EXACT template text provided below.
Copy the template word-for-word based on which fields are missing.
Only select the appropriate template - do NOT modify the wording.

---

## ONLY SHIFT MISSING (Class Captain Query)

"দয়া করে বলুন, আপনি কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

---

## ONLY DEPARTMENT MISSING (Class Captain Query)

"অনুগ্রহ করে জানান, আপনি কোন Department-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, ENT, ET, RAC, FT, MT)"

---

## ONLY SEMESTER MISSING (Class Captain Query)

"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 1st থেকে 8th পর্যন্ত)"

---

## SHIFT AND DEPARTMENT BOTH MISSING (Class Captain Query)

"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

---

## DEPARTMENT AND SEMESTER BOTH MISSING (Class Captain Query)

"দয়া করে বলুন, আপনি কোন Department এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST, 5th Semester)"

---

## SHIFT AND SEMESTER BOTH MISSING (Class Captain Query)

"দয়া করে বলুন, আপনি কোন Shift এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 2nd Shift, 5th Semester)"

---

## ALL THREE MISSING — CLASS CAPTAIN QUERY

"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"

# =======================================

# CLASS CAPTAIN CLARIFICATION RULES

# =======================================

For CLASS CAPTAIN queries (TYPE C), you MUST use the exact templates below.

Required information: Department + Shift + Semester

STEP-BY-STEP PROCESS:

1. Identify which fields are missing (missing_department, missing_shift, missing_semester)
2. Find the matching template below based on the missing combination
3. Copy the EXACT text from the template into the "clarification" field
4. Do NOT modify the wording - use it word-for-word

EXACT TEMPLATES TO COPY:

Case 1: missing_department=True, missing_shift=True, missing_semester=True
COPY THIS EXACTLY:
"দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"

Case 2: missing_department=True, missing_shift=False, missing_semester=False
COPY THIS EXACTLY:
"অনুগ্রহ করে জানান, আপনি কোন Department-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, ENT, ET, RAC, FT, MT)"

Case 3: missing_department=False, missing_shift=True, missing_semester=False
COPY THIS EXACTLY:
"দয়া করে বলুন, আপনি কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"

Case 4: missing_department=False, missing_shift=False, missing_semester=True
COPY THIS EXACTLY:
"অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 1st থেকে 8th পর্যন্ত)"

Case 5: missing_department=True, missing_shift=True, missing_semester=False
COPY THIS EXACTLY:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

Case 6: missing_department=True, missing_shift=False, missing_semester=True
COPY THIS EXACTLY:
"দয়া করে বলুন, আপনি কোন Department এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST, 5th Semester)"

Case 7: missing_department=False, missing_shift=True, missing_semester=True
COPY THIS EXACTLY:
"দয়া করে বলুন, আপনি কোন Shift এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 2nd Shift, 5th Semester)"

REMEMBER:
- All TYPE C (Class Captain) queries MUST use these exact templates
- Do NOT paraphrase or reword
- The phrase "Class Captain-এর" is mandatory in all templates
- You may add emojis at the end if you like (optional)

# =======================================

# FINAL OUTPUT RULE

# =======================================

Return ONLY valid JSON.

Use exactly these fields:

{{
  "short_info": true/false,
  "missing_department": true/false,
  "missing_shift": true/false,
  "missing_semester": true/false,
  "clarification": "..."
}}

ALWAYS:

* "not_possible" must be false if it exists in the output schema.
* If short_info=false, clarification must be an empty string.
* If short_info=true, clarification MUST contain a Bengali clarification.
* Never ask for unnecessary information.
* Never ask for Semester in TYPE B Teacher/CI queries.
* Never ask for Department/Shift/Semester in TYPE A queries.
* Class Captain queries ALWAYS require Department + Shift + Semester.
* Do NOT use routine/schedule logic.
* Do NOT classify any query as a routine/schedule query.

# =======================================
# FINAL CRITICAL REMINDER
# =======================================

Before returning your JSON output, verify:

1. If this is a CLASS CAPTAIN query (captain/ক্যাপ্টেন in query):
   → Your clarification MUST include "Class Captain-এর"
   → Find the exact matching template from the CLASS CAPTAIN CLARIFICATION RULES section above
   → COPY that template text word-for-word into the "clarification" field
   
2. Example verification:
   Query: "5th semester er class captain ke"
   → This is TYPE C (Class Captain)
   → missing_department=True, missing_shift=True, missing_semester=False
   → Use Case 5 template EXACTLY:
   → "দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"

DO NOT generate your own clarification for captain queries - ALWAYS use the exact template.
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
        
        # DEBUG: Print LLM decision
        print(f"[info_check] LLM Decision:")
        print(f"  short_info: {decision.short_info}")
        print(f"  missing_department: {decision.missing_department}")
        print(f"  missing_shift: {decision.missing_shift}")
        print(f"  missing_semester: {decision.missing_semester}")

        if decision.short_info:
            # ============================================================
            # POST-PROCESSING: Generate clarification for Captain queries
            # ============================================================
            
            # Detect if this is a captain query
            captain_keywords = ["captain", "ক্যাপ্টেন", "ক্লাস ক্যাপ্টেন", "class captain"]
            is_captain_query = any(kw in user_input.lower() for kw in captain_keywords)
            
            if is_captain_query:
                # Determine which fields are missing
                missing_dept = decision.missing_department
                missing_shift = decision.missing_shift
                missing_sem = decision.missing_semester
                
                print(f"[info_check] Captain query detected → generating exact template")
                
                # Apply exact templates based on missing combination
                if missing_dept and missing_shift and missing_sem:
                    # Case 1: All three missing
                    clarification = "দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, 2nd Shift, 5th Semester)"
                elif missing_dept and not missing_shift and not missing_sem:
                    # Case 2: Only department missing
                    clarification = "অনুগ্রহ করে জানান, আপনি কোন Department-এর Class Captain-এর তথ্য চাচ্ছেন? (যেমন: CST, ENT, ET, RAC, FT, MT)"
                elif not missing_dept and missing_shift and not missing_sem:
                    # Case 3: Only shift missing
                    clarification = "দয়া করে বলুন, আপনি কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?"
                elif not missing_dept and not missing_shift and missing_sem:
                    # Case 4: Only semester missing
                    clarification = "অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 1st থেকে 8th পর্যন্ত)"
                elif missing_dept and missing_shift and not missing_sem:
                    # Case 5: Department + Shift missing
                    clarification = "দয়া করে বলুন, আপনি কোন Department এবং কোন Shift-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST Department, 1st Shift)"
                elif missing_dept and not missing_shift and missing_sem:
                    # Case 6: Department + Semester missing
                    clarification = "দয়া করে বলুন, আপনি কোন Department এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: CST, 5th Semester)"
                elif not missing_dept and missing_shift and missing_sem:
                    # Case 7: Shift + Semester missing
                    clarification = "দয়া করে বলুন, আপনি কোন Shift এবং কোন Semester-এর Class Captain-এর তথ্য জানতে চাচ্ছেন? (যেমন: 2nd Shift, 5th Semester)"
                else:
                    # Fallback
                    clarification = "দয়া করে বলুন, আপনি কোন Department, কোন Shift, এবং কোন Semester-এর Class Captain-এর তথ্য চাচ্ছেন?"
            else:
                # Non-captain query - use LLM's clarification
                clarification = decision.clarification
            
            return {
                "sql_query": {
                    **sql_query_state,
                    "short_info": True,
                    "final_answer": clarification,
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