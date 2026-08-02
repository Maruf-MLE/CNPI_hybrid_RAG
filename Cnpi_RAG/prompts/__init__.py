"""
Prompts package initialization
"""

from .node_prompts import (
    SQL_GENERATION_PROMPT,
    get_sql_generation_prompt,
    SUPPORT_CHECK_PROMPT,
    get_support_check_prompt,
    REWRITE_QUERY_PROMPT,
    get_rewrite_query_prompt,
    METADATA_SEARCH_PROMPT
)

__all__ = [
    "SQL_GENERATION_PROMPT",
    "get_sql_generation_prompt",
    "SUPPORT_CHECK_PROMPT",
    "get_support_check_prompt",
    "REWRITE_QUERY_PROMPT",
    "get_rewrite_query_prompt",
    "METADATA_SEARCH_PROMPT",
]