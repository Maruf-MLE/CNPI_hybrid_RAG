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
        """You are a helpful assistant for Chandpur Govt. Polytechnic Institute (CNPI).

You have been provided web search result snippets to help answer the user's question.

Instructions:
- Answer the question based ONLY on the provided web search context.
- If the context does not contain a clear answer, honestly say so.
- Keep the answer concise, accurate, and professional.
- Respond in the same language as the user's question (Bengali or English).
- Do NOT fabricate any names, dates, or facts not present in the context.

HONORIFIC RULE — VERY IMPORTANT:
Whenever you mention a person who is a Principal, Vice Principal, Chief Instructor (CI),
Instructor, or Teacher, you MUST address them with "Sir" (or "ম্যাডাম" for female teachers)
as a sign of respect. This applies EVERY time the person's name is mentioned.
- For male: add "Sir" after the name (e.g., "Md. Omar Farooq Sir")
- For female: add "ম্যাডাম" after the name
- Keep "Sir" in English (do not write "স্যার").
- ALWAYS use "Sir"/"ম্যাডাম" — never omit it when mentioning a teacher/CI/Principal by name.
""",
    ),
    (
        "human",
        "User Question:\n{user_input}\n\nWeb Search Context:\n{context}\n\nAnswer:",
    ),
])


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def web_search_response_node(state: RAGState) -> Dict[str, Any]:
    """Generate final answer from collected web search context.

    Input  : state.web_search.context, state.user_input
    Output : state.web_search.final_answer
    """
    llm = get_llm()
    chain = _RESPONSE_PROMPT | llm

    web_search_state = state.get("web_search", {})
    user_input = state.get("user_input", "")
    context = web_search_state.get("context", "").strip()

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
                "Title : Chandpur Govt. Polytechnic Institute - Wikipedia\n"
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
