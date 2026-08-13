"""
No Answer Found Node - Phase 3 & 4
==================================

Triggered when retries are exhausted (max MAX_RETRIES) during support checking 
(due to hallucinations or missing information).
Generates a polite apology response using an LLM.
"""

import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
for _p in [str(plan_root), str(project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state import RAGState
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate

_NO_ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant for Chapainawabganj Polytechnic Institute (CNPI).
The information requested by the user is currently NOT available in your database.

⚠️ VERY IMPORTANT — STRUCTURE OF YOUR RESPONSE:
Your response MUST have TWO parts, and the apology MUST be VERY SHORT (just half a sentence).
Do NOT dwell on the apology or repeat it. Quickly move to the SECOND part which is the
MOST important — telling the user WHERE they can actually get the answer.

PART 1 — BRIEF APOLOGY (half a sentence, then move on):
   Just say something like "দুঃখিত, এই তথ্যটি আমার সিস্টেমে নেই।" — that's it. Do NOT
   elaborate, do NOT repeat it, do NOT say "I don't know" or "No answer found" again.

PART 2 — WHERE TO FIND THE ANSWER (the main focus of your response):
   Immediately after the brief apology, tell the user exactly WHO they should contact or
   WHERE they should go to get this information. Choose the MOST RELEVANT person/office
   based on the topic of the question:

   - Class Captain (ক্লাস ক্যাপ্টেন) → for class routine, schedule, class-related questions
   - Class Teacher (ক্লাস টিচার) → for class, attendance, student-related questions
   - Department Head / বিভাগীয় প্রধান → for department, academic, course-related questions
   - Respective Teacher/Instructor → for subject or specific course questions
   - College Office / Office Staff → for official documents, certificates, fees, admit card
   - Notice Board or College Website → for announcements, results, notices

   🔴 SPECIAL CASE — General / miscellaneous information:
   If the question is about general institute information and does not clearly fit one of
   the categories above, you MUST direct the student to the Information Officer
   (তথ্য কর্মকর্তা), Durgacharan Roy Sir (দুর্গাচরণ রায় স্যার). Tell them to contact him directly.
   Example: "এই বিষয়ে তথ্যের জন্য অনুগ্রহ করে তথ্য কর্মকর্তা দুর্গাচরণ রায় স্যারের সাথে যোগাযোগ করুন।"

RULES:
- The apology must be SHORT. The main part of your message must be about WHERE to get help.
- NEVER end with just the apology. The response MUST end by pointing the user to a person/office.
- NEVER say a blunt "I don't know" or "No answer" and stop there.
- Be polite, helpful, and student-friendly. Use simple, easy Bengali.
- Respond in the SAME language as the user's question (Bengali or English).
- Keep technical terms (Department, Shift, Chief Instructor, CNPI, etc.) in English.
- Total response: 2-3 sentences max — one short apology + one or two sentences pointing
  to the right person/office."""),
    ("human", "User question: {user_input}\n\nCurrent Date & Time: {current_datetime}")
])

def no_answer_found_node(state: RAGState) -> Dict[str, Any]:
    """Generate a polite apology when no valid answer could be produced."""
    user_input = state.get("user_input", "")
    
    print(f"[no_answer_found] Generating fallback response for query: {user_input}")
    
    llm = get_llm()
    chain = _NO_ANSWER_PROMPT | llm
    
    try:
        response = chain.invoke({
            "user_input": user_input,
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        final_answer = extract_content(response).strip()
    except Exception as e:
        print(f"[no_answer_found] Error: {e}")
        final_answer = ("দুঃখিত, এই তথ্যটি আমার সিস্টেমে নেই। এই বিষয়ে জানতে অনুগ্রহ করে "
                        "আপনার ক্লাস ক্যাপ্টেন বা ক্লাস টিচারের সাথে যোগাযোগ করুন, অথবা "
                        "তথ্য কর্মকর্তা দুর্গাচরণ রায় স্যারের সাথে যোগাযোগ করুন — "
                        "তারা আপনাকে এই তথ্য দিতে পারবেন।")

    return {
        "final_answer": final_answer,
        "answer_status": "not_found",
    }

if __name__ == "__main__":
    sample_state = {"user_input": "সিএনপিআই এর রকেটের নাম্বার দাও"}
    print(no_answer_found_node(sample_state))
