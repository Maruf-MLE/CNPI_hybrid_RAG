"""
Context Format Node
===================================

This node takes the retrieved contexts (from context_retrieve) and formats them
into a clean string for the LLM to read.

Flow: sql_query.contexts → sql_query.formatted_context
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

def context_format_node(state: RAGState) -> Dict[str, Any]:
    """
    Format contexts for LLM with date info.
    Outputs to sql_retrieve state so sql_retrieve_response can use it.
    """
    sql_query_state = state.get("sql_query", {})
    sql_retrieve_state = state.get("sql_retrieve", {})
    
    contexts = sql_query_state.get("contexts", [])
    
    if not contexts:
        print("[context_format] No contexts found to format.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "context_with_meta": "No context available.",
                "context_found": False
            }
        }
        
    print(f"[context_format] Formatting {len(contexts)} contexts.")
    
    lines = ["### Retrieved Contexts ###\n"]
    for ctx in contexts:
        rank = ctx.get("rank", 0)
        score = ctx.get("score", 0.0)
        retrieved_at = ctx.get("retrieved_at", "Unknown")
        content = ctx.get("content", "")
        
        lines.append(f"--- Context {rank} (Score: {score:.4f}, Retrieved: {retrieved_at}) ---")
        
        # Optionally add created_at/updated_at if available
        if "created_at" in ctx:
            lines.append(f"Created: {ctx['created_at']}")
        if "updated_at" in ctx:
            lines.append(f"Updated: {ctx['updated_at']}")
            
        lines.append(f"Content:\n{content}\n")
        
    formatted_context = "\n".join(lines)
    
    return {
        "sql_retrieve": {
            **sql_retrieve_state,
            "context_with_meta": formatted_context,
            "context_found": True
        }
    }

if __name__ == "__main__":
    state = {
        "sql_query": {
            "contexts": [
                {
                    "rank": 1,
                    "score": 0.95,
                    "retrieved_at": "2026-07-29",
                    "content": "The Chief Instructor of CST 2nd shift is Mr. X."
                }
            ]
        }
    }
    result = context_format_node(state)
    print(result["sql_query"]["formatted_context"])