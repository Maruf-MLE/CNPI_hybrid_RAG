"""
SQL Retrieve Create Node - Phase 3
================================

Takes the normalized query and sets it as the search query.
NO LLM IS CALLED HERE.

Flow: normalized_query -> sql_retrieve.search_query
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


def sql_retrieve_create_node(state: RAGState) -> Dict[str, Any]:
    """Take normalized query and use it directly for search, no LLM call."""
    
    sql_retrieve_state = state.get("sql_retrieve", {})
    # Use normalized_query (or rewritten_query, or user_input as fallback)
    search_query = state.get("normalized_query") or state.get("rewritten_query") or state.get("user_input", "")

    # Check if needs more info
    if sql_retrieve_state.get("need_more_info", False):
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "final_answer": "Please provide more specific information for better search results.",
            }
        }

    try:
        if not search_query:
            raise ValueError("No search query available")
            
        print(f"[sql_retrieve_create] Using direct query for search: {search_query}")
        
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "search_query": search_query.strip(),
                "final_answer": "" 
            }
        }
    except Exception as e:
        error_msg = f"Search query assignment error: {str(e)}"
        print(error_msg)
        
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "search_query": "",
                "final_answer": "Error generating search terms. Please try rephrasing your question."
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "user_input": "Tell me about the college facilities",
        "normalized_query": "college facilities details",
        "sql_retrieve": {"need_more_info": False}
    }

    result = sql_retrieve_create_node(state)
    print("Retrieve Create Result:")
    print(result)