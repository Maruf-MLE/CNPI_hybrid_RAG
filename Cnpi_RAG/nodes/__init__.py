"""
Node package initialization
"""

# Phase 1 nodes
from .entry import rewrite_query_node
from .router import llm_decide_path_node

# Phase 2 - SQL Query path nodes
from .sql_query_info_check import sql_query_info_check_node
from .sql_query_create import sql_query_create_node
from .sql_query_db_call import sql_query_db_call_node
from .sql_query_row_check_optimized import sql_query_row_check_and_optimize_node
from .sql_query_response import sql_query_response_node
from .sql_query_support_check import sql_query_support_check_node
from .fallback_dispatcher import fallback_dispatcher_node

# Phase 3 - SQL Retrieve path nodes
from .sql_retrieve_check import sql_retrieve_check_node
from .sql_retrieve_create import sql_retrieve_create_node
from .sql_retrieve_context import sql_retrieve_context_node
from .sql_retrieve_response import sql_retrieve_response_node
from .sql_retrieve_support_check import sql_retrieve_support_check_node

# Phase 4 - Web Search path nodes
from .web_search_rewrite import web_search_rewrite_node
from .web_search_docs import web_search_docs_node
from .web_search_response import web_search_response_node
from .web_search_support_check import web_search_support_check_node

# Phase 5 - Hybrid Sub-Query path nodes
from .hybrid_depth_check import hybrid_depth_check_node
from .hybrid_create_sub_questions import create_sub_questions_node
from .hybrid_dispatch_sub_queries import dispatch_sub_queries_node
from .hybrid_append_sub_answer import append_sub_answer_node
from .hybrid_merge_sub_answers import merge_sub_answers_node
from .hybrid_merge_support_check import merge_support_check_node
from .hybrid_merge_retry_check import merge_retry_check_node

__all__ = [
    # Phase 1
    "rewrite_query_node",
    "llm_decide_path_node",
    # Phase 2
    "sql_query_info_check_node",
    "sql_query_create_node",
    "sql_query_db_call_node",
    "sql_query_row_check_and_optimize_node",
    "sql_query_response_node",
    "sql_query_support_check_node",
    "fallback_dispatcher_node",
    # Phase 3
    "sql_retrieve_check_node",
    "sql_retrieve_create_node",
    "sql_retrieve_context_node",
    "sql_retrieve_response_node",
    "sql_retrieve_support_check_node",
    # Phase 4
    "web_search_rewrite_node",
    "web_search_docs_node",
    "web_search_response_node",
    "web_search_support_check_node",
    # Phase 5
    "hybrid_depth_check_node",
    "create_sub_questions_node",
    "dispatch_sub_queries_node",
    "append_sub_answer_node",
    "merge_sub_answers_node",
    "merge_support_check_node",
    "merge_retry_check_node",
]