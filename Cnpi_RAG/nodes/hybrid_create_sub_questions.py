"""
Create Sub Questions Node - Phase 5
======================================

Use the LLM to decompose the original user question into a list of smaller,
independent, answerable sub-questions.

Flow:
    state.normalized_query  →  LLM decomposition
        → hybrid.total_sub_q
        → hybrid.sub_query_list

Design Notes:
- Each sub-question should be self-contained (requires no context from others).
- Maximum 4 sub-questions to keep parallel execution bounded.
- If the LLM returns only 1 question, it is treated as a non-hybrid query;
  the dispatch node will still proceed — routing will re-enter the normal path.
- Uses structured output (Pydantic) for reliable parsing.

State written:
    hybrid.total_sub_q   (int)
    hybrid.sub_query_list (list[str])

References:
    plan/state.py → HybridPathState.total_sub_q, .sub_query_list
    plan/README.md → "Create Sub Queries" node
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_SUB_QUESTIONS: int = 4


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class SubQuestionDecompositionOutput(BaseModel):
    sub_questions: List[str] = Field(
        description=(
            "A list of 2–4 independent, self-contained sub-questions "
            "that together cover the original question completely. "
            "Each sub-question must be answerable on its own."
        )
    )
    reasoning: str = Field(
        description="One-sentence explanation of why the question was split this way."
    )


# ---------------------------------------------------------------------------
# Prompt variables
# ---------------------------------------------------------------------------

CORE_INSTRUCTIONS = f'''==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are an expert at decomposing complex questions into simpler, independent sub-questions for an information retrieval system.

YOUR TASK:
Analyze the original user question and decompose it into simpler, independent sub-questions ONLY when it contains genuinely complex multiple intents.

--------------------------------------------------
1. DECOMPOSITION RULES
--------------------------------------------------

1. Generate a minimum of 2 and a maximum of {_MAX_SUB_QUESTIONS} sub-questions.
2. Each sub-question MUST be SELF-CONTAINED.
   - Do NOT use references such as "based on the above".
   - Do NOT depend on another sub-question for context.
3. Together, the sub-questions MUST fully cover the original question.
4. Write all sub-questions in the SAME language as the original question (Bengali or English).
5. Do NOT decompose a simple question into multiple sub-questions.
6. Decompose ONLY genuinely complex multi-intent queries.

--------------------------------------------------
2. OUTPUT REQUIREMENTS
--------------------------------------------------

Return ONLY valid JSON.

The JSON must contain:
- "sub_questions": A list of sub-question strings.
- "reasoning": A one-sentence explanation of the decomposition decision.

Do NOT include:
- Markdown code fences.
- Explanations outside JSON.
- Additional fields.
- Comments.
- Any text outside the JSON object.

Follow the exact output structure defined in Layer 3.'''

PROJECT_CONFIGURATION = '''==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
- Project: CNPI Information Retrieval System.
- Institution: CNPI (Chapainawabganj Polytechnic Institute).
- Domain: College and institutional information retrieval.

DOMAIN CONTEXT:
Questions may concern different aspects of the institution, including its departments, people, academic activities, facilities, services, notices, and other institutional information.

Apply the Core Instructions to questions related to this project's domain.

This configuration can be replaced when adapting the decomposition engine to another information retrieval project.'''

EXAMPLES_REFERENCE = f'''==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

--------------------------------------------------
1. MAXIMUM SUB-QUESTION CONFIGURATION
--------------------------------------------------

Maximum allowed sub-questions:
{_MAX_SUB_QUESTIONS}

--------------------------------------------------
2. REQUIRED JSON OUTPUT STRUCTURE
--------------------------------------------------

Return exactly this JSON structure:

{{{{
  "sub_questions": [
    "Sub-question 1",
    "Sub-question 2"
  ],
  "reasoning": "One-sentence explanation of why the original question required decomposition."
}}}}

--------------------------------------------------
3. FIELD REFERENCE
--------------------------------------------------

sub_questions:
A list of independent, self-contained sub-question strings. The list must contain 2 to {_MAX_SUB_QUESTIONS} items when decomposition is required.

reasoning:
A one-sentence explanation of the decomposition decision.'''


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        CORE_INSTRUCTIONS + "\n\n" + PROJECT_CONFIGURATION + "\n\n" + EXAMPLES_REFERENCE,
    ),
    ("human", "Original question: {original_query}"),
])


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def create_sub_questions_node(state: RAGState) -> Dict[str, Any]:
    """Decompose the original query into independent sub-questions.

    Input  : state.normalized_query (or state.rewritten_query as fallback)
    Output : state.hybrid.{total_sub_q, sub_query_list}
    """
    llm = get_llm()
    # Fallback to default method for Gemini compatibility
    chain = _DECOMPOSE_PROMPT | llm.with_structured_output(SubQuestionDecompositionOutput)

    hybrid_state = state.get("hybrid", {})
    original_query = state.get("normalized_query") or state.get("rewritten_query") or state.get("user_input", "")

    if not original_query.strip():
        return {
            "hybrid": {
                **hybrid_state,
                "total_sub_q": 0,
                "sub_query_list": [],
            }
        }

    try:
        result: SubQuestionDecompositionOutput = chain.invoke(
            {"original_query": original_query}
        )

        sub_questions = result.sub_questions
        # Enforce cap
        sub_questions = sub_questions[:_MAX_SUB_QUESTIONS]

        # Deduplicate while preserving order
        seen: set = set()
        unique_sub_qs: List[str] = []
        for q in sub_questions:
            q_stripped = q.strip()
            if q_stripped and q_stripped not in seen:
                seen.add(q_stripped)
                unique_sub_qs.append(q_stripped)

        print(
            f"[create_sub_questions] Decomposed into {len(unique_sub_qs)} sub-questions. "
            f"Reasoning: {result.reasoning}"
        )

        return {
            "hybrid": {
                **hybrid_state,
                "total_sub_q": len(unique_sub_qs),
                "sub_query_list": unique_sub_qs,
            }
        }

    except Exception as e:
        print(f"[create_sub_questions] LLM error: {e} — treating as single sub-query.")
        # Fallback: treat original as the only sub-question
        return {
            "hybrid": {
                **hybrid_state,
                "total_sub_q": 1,
                "sub_query_list": [original_query],
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state = {
        "user_input": "CSE বিভাগের প্রধান কে এবং এই সপ্তাহে কোন নোটিশ প্রকাশিত হয়েছে?",
        "rewritten_query": "CSE বিভাগের প্রধান কে এবং এই সপ্তাহের নোটিশ",
        "hybrid": {
            "depth": 1,
            "total_sub_q": 0,
            "sub_query_list": [],
            "sub_query_ans": [],
            "sub_ans_count": 0,
            "merge_retries": 0,
        },
    }

    result = create_sub_questions_node(sample_state)
    print("Sub Questions:")
    for i, q in enumerate(result["hybrid"]["sub_query_list"], 1):
        print(f"  {i}. {q}")
    print(f"Total: {result['hybrid']['total_sub_q']}")
