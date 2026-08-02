"""
Package initialization files for CNPI RAG System
================================================

This package contains the implementation of the Comprehensive
Non-National Educational Public Institution Hybrid RAG System.
"""

__version__ = "1.0.0"
__author__ = "CNPI RAG Team"

from utils.llm_utils import call_llm
from utils.db_utils import execute_query

__all__ = ["call_llm", "execute_query"]