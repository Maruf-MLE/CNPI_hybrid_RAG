"""
SQL Retrieve Context Node - Phase 3
=====================================

Runs hybrid search (embedding + BM25) against the PostgreSQL documents table
and returns the ranked context with date/priority annotations.

Flow: sql_retrieve.search_query → sql_retrieve.{raw_context, context_with_meta, context_found}
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
for _p in [str(plan_root), str(project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state import RAGState
from utils.embedding_utils import hybrid_search


# =============================================================================
# Helper
# =============================================================================

def _format_result(rank: int, row: dict) -> str:
    """Format a single search result into a readable context block."""
    content = row.get("content", "").strip()
    meta = row.get("metadata") or {}

    # metadata may be a JSON string from the DB
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    date_str = meta.get("date", "তারিখ অজানা")
    author = meta.get("author", "")
    priority = meta.get("priority", "")
    score = row.get("rrf_score", 0.0)

    header_parts = [f"[{rank}]", f"তারিখ: {date_str}"]
    if author:
        header_parts.append(f"লেখক: {author}")
    if priority:
        header_parts.append(f"গুরুত্ব: {priority}")
    header_parts.append(f"(স্কোর: {score:.4f})")

    return " | ".join(header_parts) + "\n" + content


# =============================================================================
# Node
# =============================================================================

def sql_retrieve_context_node(state: RAGState) -> Dict[str, Any]:
    """Run hybrid (embedding + BM25) search and annotate results."""

    sql_retrieve_state = state.get("sql_retrieve", {})
    search_query = sql_retrieve_state.get("search_query", "").strip()

    if not search_query:
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "raw_context": "",
                "context_with_meta": "অনুসন্ধানের জন্য কোনো কীওয়ার্ড পাওয়া যায়নি।",
                "context_found": False,
            }
        }

    try:
        # Add current date & time to search query for time-sensitive retrieval
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        search_query_with_time = f"{search_query} [Current Date & Time: {current_datetime}]"
        
        results = hybrid_search(query_text=search_query_with_time)

        if not results:
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "raw_context": "",
                    "context_with_meta": "ডেটাবেজে প্রাসঙ্গিক তথ্য পাওয়া যায়নি।",
                    "context_found": False,
                }
            }

        # Build raw + formatted context
        raw_parts = [r.get("content", "") for r in results]
        formatted_parts = [_format_result(i + 1, r) for i, r in enumerate(results)]

        raw_context = "\n\n".join(raw_parts)
        context_with_meta = "\n\n---\n\n".join(formatted_parts)

        # Extract contexts list for frontend
        contexts_list = []
        for i, r in enumerate(results):
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            
            contexts_list.append({
                "rank": i + 1,
                "content": r.get("content", "").strip(),
                "date": meta.get("context_added_date", meta.get("date", "")),
                "time": meta.get("context_added_time", ""),
                "score": r.get("rrf_score", 0.0),
                "doc_type": meta.get("doc_type", ""),
                "topic": meta.get("topic", ""),
            })

        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "raw_context": raw_context,
                "context_with_meta": context_with_meta,
                "context_found": True,
                "contexts_list": contexts_list,
            }
        }

    except Exception as exc:
        error_msg = f"Hybrid search error: {exc}"
        print(error_msg)

        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "raw_context": "",
                "context_with_meta": "তথ্য সংগ্রহে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
                "context_found": False,
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    state = {
        "user_input": "NCPI-এর ইতিহাস সম্পর্কে বলুন",
        "sql_retrieve": {
            "search_query": "history of Nazrul Islamic College foundation year"
        },
    }

    result = sql_retrieve_context_node(state)
    print("Retrieve Context Result:")
    retrieve = result.get("sql_retrieve", {})
    print(f"  context_found : {retrieve.get('context_found')}")
    print(f"  context_with_meta:\n{retrieve.get('context_with_meta', '')[:400]}")