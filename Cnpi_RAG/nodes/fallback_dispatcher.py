"""
Fallback Dispatcher Node - Phase 2 -> 3 Transition
==================================================

When SQL Query path returns 0 rows, it triggers a fallback to the SQL Retrieve path.
This node acts as a bridge to properly set up the state for SQL Retrieve.

According to the architecture rules:
- Update: decided_path = "sql_retrieve"
- Reset "sql_retrieve" nested state

State read:
    None

State written:
    state.decided_path  (set to "sql_retrieve")
    state.sql_retrieve  (reset to an empty dictionary/initial state)
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

from state import RAGState, new_sql_retrieve_state


def fallback_dispatcher_node(state: RAGState) -> Dict[str, Any]:
    """Resets SQL Retrieve state and redirects decided_path.

    Returns the mutated state to LangGraph.
    """
    print("[fallback_dispatcher] Row count was 0. Switching to SQL Retrieve path.")
    return {
        "decided_path": "sql_retrieve",
        "sql_retrieve": new_sql_retrieve_state(),
    }
