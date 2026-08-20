"""
Context Format Node
===================

Formats retrieved contexts (from sql_query path) into a clean string for LLM consumption.
Handles notices, captains, teachers, and any other table data intelligently.
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
    
    Intelligently formats based on data type:
    - Notices: title_bn, content_bn, category, created_at
    - Captains: captain_name, department, shift, semester, phone, email
    - Generic: all fields dynamically
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
        # ★ Detect data type from first context's keys
        first_ctx = contexts[0] if contexts else {}
        has_notice_fields = 'title_bn' in first_ctx and 'content_bn' in first_ctx
        has_captain_fields = 'captain_name' in first_ctx and 'department' in first_ctx
        
        if has_notice_fields:
            # ★ NOTICES FORMATTING
            for i, ctx in enumerate(contexts, 1):
                notice_text = f"""=== Notice {i} ===
Notice ID: {ctx.get('notice_id', 'N/A')}
Title: {ctx.get('title_bn', '')}
Category: {ctx.get('category', 'General')}
Created At: {ctx.get('created_at', '')}

Content:
{ctx.get('content_bn', '')}

---"""
                formatted_parts.append(notice_text.strip())
        
        elif has_captain_fields:
            # ★ CAPTAIN FORMATTING (STRUCTURED & CLEAN)
            for i, ctx in enumerate(contexts, 1):
                # Determine captain type
                rank = ctx.get('captain_rank', '1')
                captain_type = "Main Captain" if rank == '1' else "Assistant Captain"
                
                captain_text = f"""=== Captain {i} ({captain_type}) ===
Name: {ctx.get('captain_name', 'N/A')}
Department: {ctx.get('department', 'N/A')}
Shift: {ctx.get('shift', 'N/A')}
Semester: {ctx.get('semester', 'N/A')}
Student ID: {ctx.get('student_id', 'N/A')}
Phone: {ctx.get('phone', 'N/A')}
Email: {ctx.get('email', 'N/A')}
Session: {ctx.get('session_year', 'N/A')}

---"""
                formatted_parts.append(captain_text.strip())
        
        else:
            # ★ GENERIC FORMATTING (for teachers, facilities, etc.)
            for i, ctx in enumerate(contexts, 1):
                ctx_text = f"=== Record {i} ===\n"
                for key, value in ctx.items():
                    if key not in ['rank']:
                        # Make field names more readable
                        field_name = key.replace('_', ' ').title()
                        ctx_text += f"{field_name}: {value}\n"
                formatted_parts.append(ctx_text.strip())
    
    # Fallback to raw_context if no formatted contexts
    if not formatted_parts and raw_context:
        formatted_parts.append(raw_context)
    
    context_with_meta = "\n\n".join(formatted_parts)
    
    print(f"[context_format] Formatted {len(formatted_parts)} context(s)")
    
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
