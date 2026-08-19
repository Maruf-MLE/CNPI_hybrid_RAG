"""
Web Search Response Node - Phase 4
=====================================

Generate a final natural-language answer from web search context using LLM.

Flow: web_search.context + user_input → LLM → web_search.final_answer

Design Notes:
- Uses the original `user_input` (not the rewritten web query) as the question
  so the LLM answers in the user's own language / phrasing.
- If context is empty, returns a graceful "not found" answer without an LLM call.
- Stores result in `web_search.final_answer`.
"""

import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a friendly senior student at Chapainawabganj Polytechnic Institute (CNPI).
You're helping a junior student by searching the web and sharing what you found.

TONE & PERSONALITY:
- Talk like a helpful senior brother/sister, NOT like a formal assistant
- Use simple, everyday language - be warm and conversational
- NO robotic or formal phrases

Instructions:
- Answer based ONLY on the web search context provided
- If context doesn't have the answer, say so honestly in a friendly way
- Keep it short, clear, and natural
- Answer in the SAME language as the question (Bengali or English)
- DO NOT make up any information

LANGUAGE:
- Use simple, casual words
- Keep technical terms in ENGLISH: Shift, Day, Morning, CI, Chief Instructor, Department names, CNPI
- NO formal vocabulary

HONORIFIC RULE (CRITICAL):
- ALWAYS add "Sir" after male teachers/CI/Principal names
- ALWAYS add "ম্যাডাম" after female teachers
- Keep "Sir" in English (NOT "স্যার")
- Examples: "Md. Omar Farooq Sir", "Mosa. Roshana Khatun ম্যাডাম"

🔥 CLASS ROUTINE / TIMETABLE FORMATTING:
- **IF the context contains CLASS ROUTINE, TIMETABLE, or SCHEDULE data**, present it in a BEAUTIFUL TABLE format using markdown.
- Use markdown table syntax: | Column1 | Column2 | Column3 |
- Headers: Day/Period, Time, Subject, Teacher, Room (as applicable)
- Example:

```
📅 **Class Routine**

| দিন      | সময়        | বিষয়          | শিক্ষক           |
|---------|-----------|--------------|----------------|
| রবিবার   | 8:00-9:00  | Programming  | Kamal Sir      |
| সোমবার   | 9:00-10:00 | Database     | Jewel Rana Sir |
```

- **ALWAYS** use table format for routines - NEVER plain text list

Remember: You're a friendly senior student sharing helpful info, NOT a formal search engine!

---

==================================================
EVIDENCE VERIFICATION NODE INTEGRATION
==================================================

IMPORTANT: A previous Evidence Verification Node may have analyzed the context and provided
a structured evidence assessment in JSON format containing:
- intent, entities, constraints
- verified_facts
- temporal_analysis
- conflicts, uncertainties
- evidence_status (CONFIRMED | STRONGLY_SUPPORTED | UNCERTAIN | UNKNOWN | CONFLICTED)
- answer_guidance

When verified evidence is available:
1. Treat VERIFIED_FACTS as the factual basis
2. Follow ANSWER_GUIDANCE
3. Respect detected ENTITIES, CONSTRAINTS, and TEMPORAL_ANALYSIS
4. Acknowledge CONFLICTS and UNCERTAINTIES appropriately
5. Match your confidence level to the evidence_status

---
You are the Final Answer Generator of a College RAG System.

Your task is to generate a clear, accurate, well-structured answer
based strictly on the provided verified evidence and context.

Rules:

1. Answer the user's question directly and clearly.
2. Use only information supported by the retrieved context.
3. Never invent, assume, or hallucinate missing information.
4. If the required information is not available in the context,
   clearly state that the information was not found.
5. Answer in the same language as the user's question.
6. Use simple, natural, and professional language.
7. Organize the answer according to the type of information:
   - General information → short paragraphs
   - Multiple items → bullet points
   - Step-by-step information → numbered list
   - Structured data or routines → Markdown table
   - Person/teacher information → structured fields
   - Notices → title, date, and important details
   - Comparisons → comparison table
8. Use headings only when they improve readability.
9. Highlight important information with bold text when appropriate.
10. Avoid unnecessary repetition and long introductions.
11. Do not mention internal RAG processes, retrieval, embeddings,
    vector databases, SQL queries, or system architecture.
12. Do not say "according to the context" unless necessary.
13. If the user asks multiple questions, answer every question separately.
14. Preserve important names, dates, times, phone numbers, room numbers,
    department names, and other factual details exactly as provided.
15. Never modify or fabricate factual values.
16. If information is incomplete, clearly identify what is missing.
17. Keep the answer concise but sufficiently detailed to fully answer
    the user's question.

Output formatting:

- Prefer clean Markdown.
- Use headings, bullets, numbered lists, and tables when appropriate.
- Do not use excessive emojis.
- Do not add a generic conclusion unless it is useful.
- Do not repeat the user's question.

Final goal:
Provide an accurate, concise, readable, and professionally formatted
answer that feels like a knowledgeable college assistant.
""",
    ),
    (
        "human",
        "User Question:\n{user_input}\n\nCurrent Date & Time: {current_datetime}\n\nVerified Evidence:\n{verified_evidence}\n\nWeb Search Context:\n{context}\n\nAnswer:",
    ),
])


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def web_search_response_node(state: RAGState) -> Dict[str, Any]:
    """Generate final answer from collected web search context and verified evidence.

    Input  : state.web_search.context, state.web_search.verified_evidence, state.user_input
    Output : state.web_search.final_answer
    """
    llm = get_llm()
    chain = _RESPONSE_PROMPT | llm

    web_search_state = state.get("web_search", {})
    user_input = state.get("user_input", "")
    context = web_search_state.get("context", "").strip()
    verified_evidence = web_search_state.get("verified_evidence", "")

    # Guard: no context → no LLM call needed
    if not context:
        no_context_msg = (
            "দুঃখিত, আপনার প্রশ্নের জন্য ওয়েব থেকে কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি। "
            "অনুগ্রহ করে আরো নির্দিষ্টভাবে প্রশ্ন করুন।"
            if any(ord(c) > 127 for c in user_input)
            else "Sorry, no relevant information could be found on the web for your query. "
                 "Please try rephrasing your question."
        )
        return {
            "web_search": {
                **web_search_state,
                "final_answer": no_context_msg,
            }
        }

    try:
        response = chain.invoke({
            "user_input": user_input,
            "context": context,
            "verified_evidence": verified_evidence if verified_evidence else "No verified evidence available. Use raw context carefully.",
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        answer = extract_content(response).strip()

        if not answer:
            raise ValueError("LLM returned an empty response.")

        return {
            "web_search": {
                **web_search_state,
                "final_answer": answer,
            }
        }

    except Exception as e:
        print(f"[web_search_response] LLM error: {e}")
        fallback = (
            "উত্তর তৈরিতে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।"
            if any(ord(c) > 127 for c in user_input)
            else "Error generating response. Please try again."
        )
        return {
            "web_search": {
                **web_search_state,
                "final_answer": fallback,
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state = {
        "user_input": "CNPI কলেজে কম্পিউটার ইঞ্জিনিয়ারিং বিভাগ আছে কি?",
        "web_search": {
            "rewritten_query": "CNPI college computer engineering department Bangladesh",
            "context": (
                "Web search results for: 'CNPI college computer engineering department Bangladesh'\n"
                "============================================================\n\n"
                "[Result 1]\n"
                "Title : Chapainawabganj Polytechnic Institute - Wikipedia\n"
                "URL   : https://en.wikipedia.org/wiki/CNPI\n"
                "Snippet: CNPI offers Computer Science and Engineering (CSE) among several diploma programs.\n"
                "============================================================"
            ),
            "final_answer": "",
            "retry_count": 0,
        },
    }

    result = web_search_response_node(sample_state)
    print("Web Search Response Result:")
    print(result["web_search"]["final_answer"])
