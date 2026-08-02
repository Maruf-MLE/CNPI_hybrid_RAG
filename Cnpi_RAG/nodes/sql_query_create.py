"""
Context Retrieve Node (formerly SQL Query Create)
===================================================

This node retrieves relevant contexts using embedding + BM25 hybrid search.
No SQL query generation - directly searches the documents table.

Flow: normalized_query → hybrid_search → contexts with timestamps
"""

import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.embedding_utils import hybrid_search


def context_retrieve_node(state: RAGState) -> dict:
    """
    Retrieve relevant contexts using embedding + BM25 hybrid search.
    
    Returns contexts with timestamps for LLM to mention when data was found.
    """
    sql_query_state = state.get("sql_query", {})

    # Use normalized_query as input
    user_query = state.get("normalized_query") or state.get("user_input", "")

    # Check if needs more info
    if sql_query_state.get("short_info", False):
        return {
            "sql_query": {
                **sql_query_state,
                "contexts": [],
                "context_found": False,
                "final_answer": "Please provide more specific information. Which department and shift are you asking about?"
            }
        }

    # Check if impossible
    if sql_query_state.get("not_possible", False):
        return {
            "sql_query": {
                **sql_query_state,
                "contexts": [],
                "context_found": False,
                "final_answer": "This query cannot be answered with available data."
            }
        }

    try:
        print(f"[context_retrieve] Searching for: {user_query}")
        
        # Perform hybrid search (embedding + BM25)
        results = hybrid_search(
            query_text=user_query,
            table_name="documents",
            top_k=5
        )

        if not results or len(results) == 0:
            print("[context_retrieve] No contexts found")
            return {
                "sql_query": {
                    **sql_query_state,
                    "contexts": [],
                    "context_found": False,
                    "final_answer": "No relevant information found in the database."
                }
            }

        print(f"[context_retrieve] Retrieved {len(results)} contexts")
        
        # Process contexts and add timestamp info
        processed_contexts = []
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for i, result in enumerate(results, 1):
            context_data = {
                "rank": i,
                "content": result.get("content", ""),
                "metadata": result.get("metadata", {}),
                "score": result.get("rrf_score", 0.0),
                "retrieved_at": current_date,
            }
            
            # Add created_at/updated_at if available in metadata
            meta = result.get("metadata", {})
            if isinstance(meta, dict):
                if "created_at" in meta:
                    context_data["created_at"] = meta["created_at"]
                if "updated_at" in meta:
                    context_data["updated_at"] = meta["updated_at"]
            
            processed_contexts.append(context_data)
            
            # Log context preview
            content_preview = str(context_data["content"])[:100]
            print(f"  [{i}] Score: {context_data['score']:.4f} | {content_preview}...")

        return {
            "sql_query": {
                **sql_query_state,
                "contexts": processed_contexts,
                "context_found": True,
                "search_query": user_query,
                "retrieved_at": current_date,
                "final_answer": ""
            }
        }

    except Exception as e:
        error_msg = f"Context retrieval error: {str(e)}"
        print(error_msg)

        return {
            "sql_query": {
                **sql_query_state,
                "contexts": [],
                "context_found": False,
                "final_answer": f"Error retrieving information: {str(e)}"
            }
        }


# Keep the old function name for backward compatibility
sql_query_create_node = context_retrieve_node


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    state = {
        "user_input": "Who is the Chief Instructor of CST 2nd shift?",
        "normalized_query": "Who is the Chief Instructor of CST 2nd shift?",
        "sql_query": {"short_info": False, "not_possible": False}
    }

    result = context_retrieve_node(state)
    print("\nContext Retrieve Result:")
    sql_state = result.get("sql_query", {})
    print(f"  Context found: {sql_state.get('context_found')}")
    print(f"  Number of contexts: {len(sql_state.get('contexts', []))}")
    print(f"  Retrieved at: {sql_state.get('retrieved_at')}")
