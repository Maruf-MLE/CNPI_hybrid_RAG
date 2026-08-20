"""
Direct Node Testing - SQL Query Path
=====================================
Test sql_query_create and sql_query_db_call nodes directly without graph.
"""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "plan"))
sys.path.insert(0, str(current_dir / "Cnpi_RAG"))

from Cnpi_RAG.nodes.sql_query_create import sql_query_create_node
from Cnpi_RAG.nodes.sql_query_db_call import sql_query_db_call_node

def test_sql_nodes():
    print("=" * 80)
    print("TESTING: sql_query_create_node + sql_query_db_call_node")
    print("=" * 80)
    
    # Test state
    state = {
        "user_input": "latest notice dao",
        "normalized_query": "latest notice dao",
        "sql_query": {}
    }
    
    print("\n[STEP 1] Calling sql_query_create_node...")
    print("-" * 80)
    result1 = sql_query_create_node(state)
    print("\nResult from sql_query_create_node:")
    sql_state = result1.get("sql_query", {})
    print(f"  query_str: {sql_state.get('query_str', 'MISSING')[:100]}...")
    print(f"  query_type: {sql_state.get('query_type', 'MISSING')}")
    print(f"  generated_at: {sql_state.get('generated_at', 'MISSING')}")
    print(f"  row_count: {sql_state.get('row_count', 'NOT SET')}")
    print(f"  contexts: {sql_state.get('contexts', 'NOT SET')}")
    
    # Update state
    state = {**state, **result1}
    
    print("\n[STEP 2] Calling sql_query_db_call_node...")
    print("-" * 80)
    result2 = sql_query_db_call_node(state)
    print("\nResult from sql_query_db_call_node:")
    sql_state2 = result2.get("sql_query", {})
    print(f"  row_count: {sql_state2.get('row_count', 'MISSING')}")
    print(f"  context_found: {sql_state2.get('context_found', 'MISSING')}")
    print(f"  contexts count: {len(sql_state2.get('contexts', []))}")
    
    if sql_state2.get('contexts'):
        print(f"\n  First context preview:")
        ctx = sql_state2['contexts'][0]
        print(f"    - notice_id: {ctx.get('notice_id')}")
        print(f"    - title_bn: {ctx.get('title_bn', '')[:50]}...")
        print(f"    - content_bn: {ctx.get('content_bn', '')[:80]}...")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_sql_nodes()
