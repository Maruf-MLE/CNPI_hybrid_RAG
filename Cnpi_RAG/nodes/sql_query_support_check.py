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
from langchain_core.messages import SystemMessage


class SupportCheckOutput(BaseModel):
    is_supported: bool = Field(description="Whether the answer is supported by context")
    reason: str = Field(description="Reasoning for the determination")


# =============================================================================
# SYSTEM PROMPT LAYERS
# =============================================================================

CORE_INSTRUCTIONS = """==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are a validation expert responsible for checking whether a generated answer is supported by the provided database context.

TASK:
Compare the generated answer against the database context and determine whether its factual claims are supported.

VALIDATION CRITERIA:

1. Set "is_supported" to TRUE if:
   - The answer contains facts, phone numbers, names, counts, or other information present in the database context.
   - The factual information in the answer is supported by the available context.

2. Set "is_supported" to FALSE if:
   - The answer contains fabricated or unsupported facts.
   - The answer includes information not found in the context.
   - The answer says "information not found" even though the context contains the requested information.

3. DATE EXCEPTION:
   - Dates are NOT required for an answer to be considered supported.
   - Only require dates when the user's question specifically asks for a date.

OUTPUT RULES:
- Return ONLY valid JSON.
- Include exactly these two fields:
  - "is_supported": boolean
  - "reason": brief reasoning.
- Do not include Markdown, explanations outside JSON, or additional fields."""

PROJECT_CONFIGURATION = """==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT:
- System: College RAG System.
- Institution: Chapainawabganj Polytechnic Institute (CNPI).
- Data source: Institutional database context.
- Validation purpose: Verify whether generated answers are factually grounded in the database context."""

EXAMPLES_AND_REFERENCE = """==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

EXPECTED OUTPUT STRUCTURE:

{
  "is_supported": true,
  "reason": "The answer's factual information is present in the database context."
}

{
  "is_supported": false,
  "reason": "The answer contains information that is not supported by the database context."
}

DATE HANDLING:
- If the answer omits a date that was not requested, this alone does not make the answer unsupported.
- If the question specifically asks for a date, the date must be supported by the context."""

# Combine system prompt layers
SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_AND_REFERENCE}"

_SUPPORT_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),
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