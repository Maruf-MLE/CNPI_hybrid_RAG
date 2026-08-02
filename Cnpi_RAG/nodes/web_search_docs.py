"""
Web Search Docs Node - Phase 4
================================

Perform a real web search using DuckDuckGo and collect/parse document context.

Flow: web_search.rewritten_query → [DuckDuckGo] → web_search.context

Design Notes:
- Uses `duckduckgo_search` (free, no API key required).
- Fetches top-N results and parses snippet + title + URL into structured context.
- Stores combined context string in `web_search.context`.
- On zero results, sets `web_search.context = ""` (response node handles gracefully).
- `requests` + simple text extraction is used to optionally fetch page bodies.
  Full HTML scraping is intentionally not done here to keep latency low and
  avoid JS-heavy pages; snippets from DDGS are sufficient for initial context.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState

# ---------------------------------------------------------------------------
# DuckDuckGo search helper
# ---------------------------------------------------------------------------

_MAX_RESULTS: int = 5          # How many DDGS results to retrieve
_MAX_BODY_CHARS: int = 800     # Max chars to keep from each snippet


def _ddg_search(query: str, max_results: int = _MAX_RESULTS) -> List[Dict[str, str]]:
    """Run a DuckDuckGo text search and return a list of result dicts.

    Each dict has keys: 'title', 'href', 'body' (snippet).

    Falls back to an empty list on any error (network issue, rate-limit, etc.).
    """
    try:
        from duckduckgo_search import DDGS  # pip install duckduckgo-search

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", "").strip(),
                    "href":  r.get("href", "").strip(),
                    "body":  r.get("body", "").strip()[:_MAX_BODY_CHARS],
                })
        return results

    except ImportError:
        print(
            "[web_search_docs] 'duckduckgo_search' not installed. "
            "Run: pip install duckduckgo-search"
        )
        return []
    except Exception as e:
        print(f"[web_search_docs] DuckDuckGo search error: {e}")
        return []


def _format_results_as_context(results: List[Dict[str, str]], query: str) -> str:
    """Convert raw search results into a readable context string for the LLM."""
    if not results:
        return ""

    lines = [f"Web search results for: '{query}'\n{'=' * 60}"]
    for i, r in enumerate(results, start=1):
        lines.append(
            f"\n[Result {i}]\n"
            f"Title : {r['title']}\n"
            f"URL   : {r['href']}\n"
            f"Snippet: {r['body']}"
        )
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def web_search_docs_node(state: RAGState) -> Dict[str, Any]:
    """Search the web and collect document context.

    Input  : state.web_search.rewritten_query
    Output : state.web_search.context
    """
    web_search_state = state.get("web_search", {})
    query = web_search_state.get("rewritten_query", "").strip()

    # If no query, propagate empty context
    if not query:
        print("[web_search_docs] No query provided — skipping web search.")
        return {
            "web_search": {
                **web_search_state,
                "context": "",
            }
        }

    print(f"[web_search_docs] Searching for: '{query}'")

    try:
        results = _ddg_search(query, max_results=_MAX_RESULTS)
        context = _format_results_as_context(results, query)

        print(
            f"[web_search_docs] Retrieved {len(results)} result(s). "
            f"Context length: {len(context)} chars."
        )

        return {
            "web_search": {
                **web_search_state,
                "context": context,
            }
        }

    except Exception as e:
        print(f"[web_search_docs] Unexpected error: {e}")
        return {
            "web_search": {
                **web_search_state,
                "context": "",
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state = {
        "web_search": {
            "rewritten_query": "CNPI college CSE department head Bangladesh",
            "context": "",
            "final_answer": "",
            "retry_count": 0,
        }
    }

    result = web_search_docs_node(sample_state)
    print("\nWeb Search Docs Result:")
    ctx = result.get("web_search", {}).get("context", "")
    print(ctx if ctx else "(no context collected)")
