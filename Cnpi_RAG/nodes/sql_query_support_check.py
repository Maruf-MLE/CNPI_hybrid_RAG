"""
SQL Query Support Check Node - Phase 2
=======================================

Validate if answer is supported by database context with retry mechanism.

Flow: sql_query.final_answer + context → validate → retry or complete
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


class SupportCheckOutput(BaseModel):
    is_supported: bool = Field(description="Whether the answer is supported by context")
    reason: str = Field(description="Reasoning for the determination")


_SUPPORT_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a validation expert. Check if the generated answer is supported by the database context.

Return ONLY JSON with:
- "is_supported": boolean
- "reason": brief reasoning

Criteria:
- is_supported = True if the answer contains facts, phone numbers, names, counts, or information present in the context.
- is_supported = False if the answer hallucinates facts not found in the context or says 'information not found' when context had real data.
- Note: Dates are NOT required unless the question specifically asked for a date."""),
    ("human", "Context:\n{context}\n\nAnswer:\n{answer}")
])


def sql_query_support_check_node(state: RAGState) -> dict:
    """Validate answer support with retry mechanism."""
    llm = get_llm()
    support_check_chain = _SUPPORT_CHECK_PROMPT | llm.with_structured_output(SupportCheckOutput)

    sql_query_state = state.get("sql_query", {})
    context = sql_query_state.get("optimized_context", "") or sql_query_state.get("raw_context", "")
    final_answer = sql_query_state.get("final_answer", "")
    retry_count = sql_query_state.get("retry_count", 0)

    if not final_answer or "No database information was found" in final_answer:
        return {
            "answer_status": "not_found",
            "sql_query": {
                **sql_query_state,
                "answer_status": "not_found"
            }
        }

    try:
        result = support_check_chain.invoke({
            "context": context,
            "answer": final_answer
        })

        if result.is_supported:
            return {
                "final_answer": final_answer,
                "answer_status": "found",
                "sql_query": {
                    **sql_query_state,
                    "answer_status": "found",
                    "final_answer": final_answer
                }
            }
        else:
            if retry_count < 3:
                return {
                    "sql_query": {
                        **sql_query_state,
                        "retry_count": retry_count + 1,
                        "answer_status": "not_found"
                    }
                }
            else:
                return {
                    "final_answer": final_answer,
                    "answer_status": "found",
                    "sql_query": {
                        **sql_query_state,
                        "answer_status": "found",
                        "final_answer": final_answer
                    }
                }

    except Exception as e:
        print(f"Support validation error: {e}")
        return {
            "final_answer": final_answer,
            "answer_status": "found",
            "sql_query": {
                **sql_query_state,
                "answer_status": "found",
                "final_answer": final_answer
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    state = {
        "sql_query": {
            "final_answer": "Md. Rejuanul Arefin's phone is +8801731818181.",
            "raw_context": "name_en: Md. Rejuanul Arefin\nphone_primary: +8801731818181",
            "retry_count": 0
        }
    }
    result = sql_query_support_check_node(state)
    print("Support Check Result:", result)