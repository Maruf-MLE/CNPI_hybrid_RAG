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

Evaluate the retrieved answer against the provided context and query.

Return EXACTLY ONE of the following three words:

1. **"yes"**: The retrieved answer is factually correct and supported by the context. The answer does not need to be explicitly stated in the context. If the AI derives a logically valid and accurate answer using the available contextual information, return "yes".

2. **"no_support"**: The context does not contain sufficient information to answer the query, and the retrieved answer cannot be reliably derived from the available context.

3. **"hallucination"**: The context contains sufficient information to answer the query, but the retrieved answer is factually incorrect, contradicts the context, or includes fabricated information.

**Important Rules:**
- Do not require an exact sentence match between the context and answer.
- Accept logically valid conclusions and reasonable inferences derived from the context.
- Do not classify a correct, context-based inference as hallucination merely because it is not explicitly mentioned.
- Do not assume missing information or use external knowledge to justify an answer.
- Evaluate factual correctness, not wording similarity.

**Strict Date and Number Verification:**
- Always verify every date, year, time, number, and factual detail against the context.
- Never accept an answer as "yes" if it contains even one incorrect date, year, time, or numerical value.
- Pay special attention to publication dates and event dates. Do not confuse them.
- A correct inference does not justify an incorrect factual detail.
- If the answer is partially correct but contains a factual error, return "hallucination".

**Critical Classification Rules:**

1. If the query asks for information that is not explicitly available in the context, but the retrieved answer correctly acknowledges that the information is unavailable, classify it as "yes".

2. If the retrieved answer provides other relevant information that is available in the context (such as a notice publication date), and that information is factually correct, classify it as "yes".

3. Do not classify an answer as "no_support" merely because the exact requested information is missing from the context. If the AI correctly identifies and communicates that the information is missing, the answer is correct.

4. Do not classify an answer as "hallucination" simply because it says that information is unavailable. Hallucination applies only when the answer contains fabricated, incorrect, or context-contradicting factual claims.

5. If the answer correctly distinguishes between an event date and a notice publication date, accept it as "yes".

**Examples:**

Context: Notice Publication Date: 2026-10-16. The notice states that a teacher was affected by dengue, but does not mention when he was infected.

Query: On which date was the teacher infected with dengue?

Retrieved Answer: The exact date of infection is not mentioned in the available information. However, the related notice was published on 2026-10-16.

Expected Output: yes

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
                },
                "answer_status": "found",
                "final_answer": answer,
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