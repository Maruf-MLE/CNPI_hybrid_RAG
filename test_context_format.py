"""
Test Context Format Node
=========================
Test if context_format_node properly formats captain and notice data.
"""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "plan"))
sys.path.insert(0, str(current_dir / "Cnpi_RAG"))

from Cnpi_RAG.nodes.sql_query_create import sql_query_create_node
from Cnpi_RAG.nodes.sql_query_db_call import sql_query_db_call_node
from Cnpi_RAG.nodes.context_format import context_format_node

def test_context_format():
    print("=" * 80)
    print("TESTING: Context Format Node")
    print("=" * 80)
    
    # Test 1: Captain Query
    print("\n" + "=" * 80)
    print("TEST 1: Captain Query - CST department er captain")
    print("=" * 80)
    
    state = {
        "user_input": "CST department er captain",
        "normalized_query": "CST department er captain",
        "sql_query": {}
    }
    
    # Step 1: Generate SQL
    state = {**state, **sql_query_create_node(state)}
    
    # Step 2: Execute SQL
    state = {**state, **sql_query_db_call_node(state)}
    
    sql_state = state.get("sql_query", {})
    row_count = sql_state.get("row_count", 0)
    print(f"\n[SQL Result] Found {row_count} row(s)")
    
    if row_count > 0:
        # Step 3: Format contexts
        print("\n[Formatting contexts...]")
        format_result = context_format_node(state)
        
        sql_retrieve_state = format_result.get("sql_retrieve", {})
        formatted_context = sql_retrieve_state.get("context_with_meta", "")
        
        print("\n" + "="*80)
        print("FORMATTED CONTEXT FOR CAPTAIN:")
        print("="*80)
        print(formatted_context)
        print("="*80)
    else:
        print("❌ No data to format")
    
    # Test 2: Notice Query
    print("\n\n" + "=" * 80)
    print("TEST 2: Notice Query - latest notice dao")
    print("=" * 80)
    
    state2 = {
        "user_input": "latest notice dao",
        "normalized_query": "latest notice dao",
        "sql_query": {}
    }
    
    # Step 1: Generate SQL
    state2 = {**state2, **sql_query_create_node(state2)}
    
    # Step 2: Execute SQL
    state2 = {**state2, **sql_query_db_call_node(state2)}
    
    sql_state2 = state2.get("sql_query", {})
    row_count2 = sql_state2.get("row_count", 0)
    print(f"\n[SQL Result] Found {row_count2} row(s)")
    
    if row_count2 > 0:
        # Step 3: Format contexts
        print("\n[Formatting contexts...]")
        format_result2 = context_format_node(state2)
        
        sql_retrieve_state2 = format_result2.get("sql_retrieve", {})
        formatted_context2 = sql_retrieve_state2.get("context_with_meta", "")
        
        print("\n" + "="*80)
        print("FORMATTED CONTEXT FOR NOTICE:")
        print("="*80)
        print(formatted_context2[:500] + "...")  # Show first 500 chars
        print("="*80)
    else:
        print("❌ No data to format")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_context_format()
