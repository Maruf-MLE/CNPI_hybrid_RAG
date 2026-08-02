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
# Prompt
# ---------------------------------------------------------------------------

_WEB_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert at reformulating questions into effective web search queries.

Your task:
- Take the user's original question (possibly in Bengali/Bangla or English).
- Rewrite it into a SHORT, KEYWORD-RICH English query suitable for web search engines.
- Focus on the core information need; remove conversational filler.
- Add relevant context keywords (e.g. "Bangladesh", "CNPI college", "government college") if they help narrow the search.
- The query should be 3–10 words maximum.

Return ONLY valid JSON with keys:
- "rewritten_query": the optimized web search string
- "reasoning": one-sentence explanation of changes made
""",
    ),
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
            "web_search": {
                **web_search_state,
                "rewritten_query": rewritten,
            }
        }

    except Exception as e:
        print(f"[web_search_rewrite] LLM error: {e} — using original query as fallback.")
        return {
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
