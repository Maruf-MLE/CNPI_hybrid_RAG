"""
Web Search Support Check Node - Phase 4
==========================================

Validate whether the generated web-search answer is actually supported by
the collected web context. Implements the same retry/support pattern used in
Phase 2 (sql_query_support_check) and Phase 3 (sql_retrieve_support_check).

Flow:
    web_search.final_answer + web_search.context
        → LLM validation
        → is_supported?
            Yes → finalize (answer_status="found", top-level final_answer updated)
            No  → increment retry_count (graph routes back to web_search_docs / response)

Retry cap: MAX_RETRIES (3) — defined in state.py.

State written:
    web_search.final_answer  (may be replaced with "not found" message on exhaustion)
    web_search.retry_count   (incremented on failure)
    answer_status            (top-level: "found" | "not_found")
    final_answer             (top-level: copied from web_search.final_answer on success)
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

from state import RAGState, MAX_RETRIES
from utils.llm_utils import get_llm
from langchain_core.prompts import ChatPromptTemplate


from typing import Literal

# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class WebSupportCheckOutput(BaseModel):
    support_status: Literal["yes", "no_support", "hallucination"] = Field(
        description=(
            "'yes' if answer is supported. "
            "'no_support' if the context completely lacks the required info. "
            "'hallucination' if context has info but answer is factually wrong."
        )
    )
    reason: str = Field(description="One-sentence reasoning for the decision.")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SUPPORT_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a factual accuracy validator.

Given a question, a web-search context, and a generated answer, determine
whether the answer is ACTUALLY SUPPORTED by the context.

Return ONLY valid JSON matching the schema.
Choose support_status:
- 'yes': The answer uses facts, dates, or names present in the context.
- 'no_support': The web context has NO relevant information to answer the question.
- 'hallucination': The context has information, but the answer is wrong or made up.
""",
    ),
    (
        "human",
        "Question: {question}\n\nWeb Context:\n{context}\n\nGenerated Answer:\n{answer}",
    ),
])


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def web_search_support_check_node(state: RAGState) -> Dict[str, Any]:
    """Validate web-search answer quality and handle retry logic.

    Input  : state.web_search.{final_answer, context, retry_count}, state.user_input
    Output : state.web_search.{final_answer, retry_count},
             state.answer_status, state.final_answer (top-level, on success)
    """
    llm = get_llm()
    chain = _SUPPORT_CHECK_PROMPT | llm.with_structured_output(WebSupportCheckOutput)

    web_search_state = state.get("web_search", {})
    user_input = state.get("user_input", "")
    answer = web_search_state.get("final_answer", "").strip()
    context = web_search_state.get("context", "").strip()
    retry_count = web_search_state.get("retry_count", 0)

    # ------------------------------------------------------------------
    # Guard: nothing to validate
    # ------------------------------------------------------------------
    if not answer:
        return {
            "web_search": {
                **web_search_state,
                "final_answer": (
                    "ওয়েব সার্চ থেকে কোনো উত্তর তৈরি হয়নি।"
                    if any(ord(c) > 127 for c in user_input)
                    else "No answer was generated from web search."
                ),
                "retry_count": retry_count,
            },
            "answer_status": "not_found",
        }

    # ------------------------------------------------------------------
    # Guard: retry cap exceeded — give up gracefully
    # ------------------------------------------------------------------
    if retry_count >= MAX_RETRIES:
        return {
            "web_search": {
                **web_search_state,
                "final_answer": (
                    "একাধিক চেষ্টার পরেও ওয়েব থেকে নির্ভরযোগ্য উত্তর পাওয়া যায়নি। "
                    "অনুগ্রহ করে প্রশ্নটি পরিবর্তন করে আবার চেষ্টা করুন।"
                    if any(ord(c) > 127 for c in user_input)
                    else (
                        "A reliable answer could not be found via web search after "
                        f"{MAX_RETRIES} attempts. Please rephrase your question."
                    )
                ),
                "retry_count": retry_count,
            },
            "answer_status": "not_found",
        }

    # ------------------------------------------------------------------
    # LLM validation
    # ------------------------------------------------------------------
    try:
        result: WebSupportCheckOutput = chain.invoke({
            "question": user_input,
            "context": context or "(no context available)",
            "answer": answer,
        })

        if result.support_status == "yes":
            # ✅ Supported — bubble up to top-level fields for Django / Hybrid
            return {
                "web_search": {
                    **web_search_state,
                    "final_answer": answer,
                    "retry_count": retry_count,
                },
                "final_answer": answer,
                "answer_status": "found",
            }
        elif result.support_status == "no_support":
            # ❌ No support in context — do not retry, pass to no_answer_found immediately
            print(f"[web_search_support_check] No support in context. Skipping retries.")
            return {
                "web_search": {
                    **web_search_state,
                    "retry_count": MAX_RETRIES,
                    "final_answer": "",
                },
                "answer_status": "not_found",
            }
        else:
            # ❌ Hallucination — increment retry; graph will loop back to response
            new_retry = retry_count + 1
            print(
                f"[web_search_support_check] Hallucination detected "
                f"(retry {new_retry}/{MAX_RETRIES}). Reason: {result.reason}"
            )
            return {
                "web_search": {
                    **web_search_state,
                    "retry_count": new_retry,
                    # Clear the bad answer so the response node generates a fresh one
                    "final_answer": "",
                },
                "answer_status": "not_found",
            }

    except Exception as e:
        print(f"[web_search_support_check] LLM validation error: {e}")
        new_retry = retry_count + 1

        if new_retry >= MAX_RETRIES:
            return {
                "web_search": {
                    **web_search_state,
                    "retry_count": new_retry,
                    "final_answer": (
                        f"যাচাইকরণে সমস্যা হয়েছে ({e})। অনুগ্রহ করে আবার চেষ্টা করুন।"
                        if any(ord(c) > 127 for c in user_input)
                        else f"Validation error: {e}. Please try again."
                    ),
                },
                "answer_status": "not_found",
            }

        return {
            "web_search": {
                **web_search_state,
                "retry_count": new_retry,
                "final_answer": "",  # trigger fresh response on retry
            },
            "answer_status": "not_found",
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state = {
        "user_input": "CNPI কলেজে কম্পিউটার বিভাগ আছে কি?",
        "web_search": {
            "rewritten_query": "CNPI college CSE department Bangladesh",
            "context": (
                "[Result 1] Title: CNPI – Wikipedia\n"
                "Snippet: CNPI offers Computer Science and Engineering (CSE) diploma programs."
            ),
            "final_answer": (
                "হ্যাঁ, CNPI কলেজে কম্পিউটার সায়েন্স অ্যান্ড ইঞ্জিনিয়ারিং (CSE) বিভাগ আছে।"
            ),
            "retry_count": 0,
        },
    }

    result = web_search_support_check_node(sample_state)
    print("Support Check Result:")
    print(f"  answer_status : {result.get('answer_status')}")
    print(f"  final_answer  : {result.get('web_search', {}).get('final_answer')}")
    print(f"  retry_count   : {result.get('web_search', {}).get('retry_count')}")
