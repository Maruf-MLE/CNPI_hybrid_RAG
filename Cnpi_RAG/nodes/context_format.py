"""
Context Format Node
===================

Formats retrieved contexts (from sql_query path) into a clean string for LLM consumption.
Handles both notices data and other query results.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState


def context_format_node(state: RAGState) -> dict:
    """
    Format retrieved contexts into a clean string for sql_retrieve_response node.
    
    For notices: formats title_bn, content_bn, category, created_at
    For other data: uses raw_context
    """
    sql_query_state = state.get("sql_query", {})
    contexts = sql_query_state.get("contexts", [])
    raw_context = sql_query_state.get("raw_context", "")
    
    if not contexts and not raw_context:
        return {
            "sql_retrieve": {
                "context_with_meta": "",
                "context_found": False
            }
        }
    
    # Format contexts for LLM
    formatted_parts = []
    
    if contexts:
        # ★ Notice-specific formatting
        query_type = sql_query_state.get("query_type", "")
        
        if query_type == "notices_query":
            # Format as notices
            for i, ctx in enumerate(contexts, 1):
                notice_text = f"""
=== Notice {i} ===
Notice ID: {ctx.get('notice_id', 'N/A')}
Title: {ctx.get('title_bn', '')}
Category: {ctx.get('category', 'General')}
Created At: {ctx.get('created_at', '')}

Content:
{ctx.get('content_bn', '')}

---
"""
                formatted_parts.append(notice_text.strip())
        else:
            # Generic context formatting
            for i, ctx in enumerate(contexts, 1):
                ctx_text = f"=== Context {i} ===\n"
                for key, value in ctx.items():
                    if key not in ['rank']:
                        ctx_text += f"{key}: {value}\n"
                formatted_parts.append(ctx_text.strip())
    
    # Fallback to raw_context if no formatted contexts
    if not formatted_parts and raw_context:
        formatted_parts.append(raw_context)
    
    context_with_meta = "\n\n".join(formatted_parts)
    
    return {
        "sql_retrieve": {
            "context_with_meta": context_with_meta,
            "context_found": bool(context_with_meta.strip())
        }
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    state = {
        "sql_query": {
            "query_type": "notices_query",
            "contexts": [
                {
                    "rank": 1,
                    "notice_id": 123,
                    "title_bn": "ভর্তি বিজ্ঞপ্তি ২০২৬",
                    "content_bn": "চাঁপাইনবাবগঞ্জ পলিটেকনিক ইনস্টিটিউটে ভর্তি চলছে...",
                    "category": "Admission",
                    "created_at": "2026-08-10 14:30:00"
                }
            ]
        }
    }
    
    result = context_format_node(state)
    print("Formatted Context:")
    print(result["sql_retrieve"]["context_with_meta"])
