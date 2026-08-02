"""
SQL Retrieve Support Check Node - Phase 3
==========================================

Validates whether the LLM-generated answer is supported by the retrieved context.

Retry logic:
    - If LLM says "no" (not supported) AND retry_count < MAX_RETRIES
      → set supported=False, increment retry_count
      → graph routes back to sql_retrieve_response (same context, fresh LLM call)
    - If LLM says "yes" OR retry_count >= MAX_RETRIES
      → set supported=True → graph routes to END

State read:
    sql_retrieve.final_answer       → the answer to verify
    sql_retrieve.context_with_meta  → the context used
    sql_retrieve.retry_count        → how many times we have already retried

State written:
    sql_retrieve.supported     → True / False
    sql_retrieve.retry_count   → incremented on failure
"""

import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
for _p in [str(plan_root), str(project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state import RAGState, MAX_RETRIES
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


_SUPPORT_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a quality assurance checker for CNPI information retrieval.

Evaluate the retrieved answer against the context and query.
Return EXACLTY ONE of the following three words:

1. "yes" : The context supports the answer, it is complete, accurate, and correct.
2. "no_support" : The context DOES NOT contain the information needed to answer the query. (Missing info)
3. "hallucination" : The context HAS the information, but the answer is factually incorrect, made up, or hallucinated.

Return only "yes", "no_support", or "hallucination"."""),
    ("human", "Query: {user_input}\n\nAnswer: {answer}\n\nContext: {context}")
])


def sql_retrieve_support_check_node(state: RAGState) -> Dict[str, Any]:
    """Check if retrieved answer is supported and quality acceptable.

    Sets sql_retrieve.supported = True  → graph routes to END
          sql_retrieve.supported = False → graph retries sql_retrieve_response
    retry_count is incremented on each failed check (max MAX_RETRIES = 3).
    """
    llm = get_llm()
    chain = _SUPPORT_CHECK_PROMPT | llm

    sql_retrieve_state = state.get("sql_retrieve", {})
    user_input = state.get("user_input", "")
    answer = sql_retrieve_state.get("final_answer", "")
    context = sql_retrieve_state.get("context_with_meta", "")
    retry_count = sql_retrieve_state.get("retry_count", 0)

    print(f"[sql_retrieve_support_check] retry_count={retry_count}, answer_len={len(answer)}")

    # Guard: no answer or retries exhausted → force exit
    if not answer.strip() or retry_count >= MAX_RETRIES:
        print("[sql_retrieve_support_check] Exiting — no answer or max retries reached.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": True,      # force exit from retry loop
                "retry_count": retry_count,
            }
        }

    try:
        response = chain.invoke({
            "user_input": user_input,
            "answer": answer,
            "context": context,
        })

        check_result = extract_content(response).strip().lower()

        print(f"[sql_retrieve_support_check] LLM verdict: '{check_result}'")

        if "yes" in check_result:
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "supported": True,
                    "retry_count": retry_count,
                }
            }
        elif "no_support" in check_result:
            print("[sql_retrieve_support_check] No support in context. Skipping retries.")
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "supported": False,
                    "retry_count": MAX_RETRIES,  # Force it to exit/fail immediately
                }
            }
        else:
            # Assumed hallucination or other failure -> retry
            new_retry_count = retry_count + 1
            print(f"[sql_retrieve_support_check] Hallucination detected. Retry {new_retry_count}/{MAX_RETRIES}.")
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "supported": False,
                    "retry_count": new_retry_count,
                }
            }

    except Exception as e:
        print(f"[sql_retrieve_support_check] Error: {e}. Treating as supported to avoid loop.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": True,
                "retry_count": retry_count,
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "user_input": "What facilities are available at the college?",
        "sql_retrieve": {
            "final_answer": "The college has a library, computer lab, sports ground, and auditorium.",
            "context_with_meta": "Date: 2024-01-15\nInformation: library, computer lab, sports ground, auditorium.",
            "retry_count": 0,
        }
    }
    result = sql_retrieve_support_check_node(sample_state)
    print("Support Check Result:")
    print(result)