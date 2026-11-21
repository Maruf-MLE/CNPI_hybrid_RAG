"""
Web Search Rewrite Node - Phase 4
==================================

Rewrite the user query into a web-search-friendly English query using LLM.

Flow: state.normalized_query → web_search.rewritten_query (web-optimized)

Design Notes:
- Uses the top-level `normalized_query` (entity-normalized) as base input.
- Rewrites it specifically for external web search (shorter, keyword-rich, English).
- Stores result in nested `web_search.rewritten_query` (WebSearchPathState).
- Does NOT mutate the top-level `normalized_query` (Phase 1 output is preserved).
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

from state import RAGState
from utils.llm_utils import get_llm
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class WebQueryRewriteOutput(BaseModel):
    rewritten_query: str = Field(
        description=(
            "A concise, keyword-rich English web search query "
            "suitable for search engines like Google / DuckDuckGo."
        )
    )
    reasoning: str = Field(
        description="Brief explanation of how the query was reformulated."
    )


# ---------------------------------------------------------------------------
# Prompt Components
# ---------------------------------------------------------------------------

CORE_INSTRUCTIONS = """==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are an expert at reformulating user questions into effective web search queries.

TASK:
Convert the user's original question into a short, keyword-rich English search query optimized for web search engines.

PROCESSING RULES:
1. Accept the original question in Bengali/Bangla or English.
2. Identify the core information need.
3. Remove conversational filler and unnecessary words.
4. Rewrite the question using concise, relevant English keywords.
5. Add relevant context keywords when they help narrow or improve search relevance.
6. Keep the rewritten query between 3 and 10 words maximum.

OUTPUT RULES:
- Return ONLY valid JSON.
- Do not include Markdown, code fences, explanations, or text outside the JSON.
- The JSON must contain exactly these keys:
  - "rewritten_query": The optimized English web search query.
  - "reasoning": A one-sentence explanation of the changes made.

OUTPUT FORMAT:
{
  "rewritten_query": "Optimized English search query",
  "reasoning": "One-sentence explanation of the changes made."
}"""

PROJECT_CONFIGURATION = """==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
- Institution: Chapainawabganj Polytechnic Institute (CNPI).
- Country: Bangladesh.
- Domain: Educational and institutional information.
- Search purpose: Find relevant information about CNPI and its educational or institutional context.

SEARCH CONTEXT:
When relevant to the user's question, consider adding context keywords such as:
- Bangladesh
- CNPI college
- government college

Use only context keywords that genuinely help narrow the search. Do not add irrelevant keywords."""

EXAMPLES_REFERENCE = """==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

A. INPUT LANGUAGE REFERENCE
The original user question may be written in:
- Bengali
- Bangla
- English

Regardless of the input language, the rewritten search query must be in English.

B. QUERY OPTIMIZATION REFERENCE

Original question:
"Who is the principal of CNPI?"

Optimized query:
"CNPI current principal Bangladesh"

Reasoning:
"Removed conversational wording and added relevant location context to narrow the search."

C. CONTEXT KEYWORD REFERENCE

Possible context keywords:
- Bangladesh
- CNPI college
- government college

These are examples, not mandatory keywords. Include them only when relevant."""

WEB_SEARCH_REWRITE_SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_REFERENCE}"

_WEB_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=WEB_SEARCH_REWRITE_SYSTEM_PROMPT),
    ("human", "Original query: {original_query}"),
])


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def web_search_rewrite_node(state: RAGState) -> Dict[str, Any]:
    """Rewrite the user query into a web-search-friendly string.

    Input  : state.normalized_query  (Phase 1 entity-normalized output)
    Output : state.web_search.rewritten_query
    """
    llm = get_llm()
    chain = _WEB_REWRITE_PROMPT | llm.with_structured_output(WebQueryRewriteOutput)

    web_search_state = state.get("web_search", {})

    # Use Phase-1 normalized_query as base; fall back to user_input
    original_query = state.get("normalized_query") or state.get("user_input", "")

    if not original_query.strip():
        # Nothing to search — propagate an empty rewritten_query; docs node will handle it
        return {
            "web_search": {
                **web_search_state,
                "rewritten_query": "",
            }
        }

    try:
        result: WebQueryRewriteOutput = chain.invoke({"original_query": original_query})
        rewritten = result.rewritten_query.strip()

        # Safety: if LLM returned nothing useful, fall back to original
        if not rewritten:
            rewritten = original_query

        return {
            "decided_path": "web_search",
            "web_search": {
                **web_search_state,
                "rewritten_query": rewritten,
            }
        }

    except Exception as e:
        print(f"[web_search_rewrite] LLM error: {e} — using original query as fallback.")
        return {
            "decided_path": "web_search",
            "web_search": {
                **web_search_state,
                "rewritten_query": original_query,
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state = {
        "user_input": "কম্পিউটার বিজ্ঞান বিভাগের প্রধান কে?",
        "rewritten_query": "CNPI কলেজে কম্পিউটার বিজ্ঞান বিভাগের বিভাগীয় প্রধান",
        "web_search": {
            "rewritten_query": "",
            "context": "",
            "final_answer": "",
            "retry_count": 0,
        },
    }

    result = web_search_rewrite_node(sample_state)
    print("Web Search Rewrite Result:")
    print(result)
