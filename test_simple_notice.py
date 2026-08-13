"""
Simple Test for Notice Query Path
==================================

Tests only the SQL query creation and execution.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "Cnpi_RAG"))
sys.path.insert(0, str(project_root / "plan"))

from Cnpi_RAG.nodes.sql_query_create import sql_query_create_node


def test_simple_notice_query():
    """Test SQL query generation and execution."""
    
    print("=" * 80)
    print("SIMPLE NOTICE QUERY TEST")
    print("=" * 80)
    
    test_queries = [
        "latest notice dao",
        "সর্বশেষ নোটিশ",
        "last 5 notices",
        "শেষ ৩টি নোটিশ দেখাও"
    ]
    
    for query in test_queries:
        print(f"\n{'─' * 80}")
        print(f"Query: {query}")
        print('─' * 80)
        
        state = {
            "user_input": query,
            "normalized_query": query,
            "sql_query": {}
        }
        
        try:
            result = sql_query_create_node(state)
            sql_state = result.get("sql_query", {})
            
            print(f"\n✓ SQL Generated:")
            print(f"  {sql_state.get('query_str', 'NO QUERY')}")
            
            print(f"\n✓ Row Count: {sql_state.get('row_count', 0)}")
            
            if sql_state.get("contexts"):
                print(f"\n✓ Retrieved {len(sql_state['contexts'])} notice(s):")
                for i, ctx in enumerate(sql_state['contexts'], 1):
                    title = ctx.get('title_bn', 'No title')[:50]
                    created = ctx.get('created_at', 'Unknown')
                    print(f"  [{i}] {title}... (Created: {created})")
            
            if sql_state.get("final_answer"):
                print(f"\n⚠ Final Answer: {sql_state['final_answer']}")
                
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print('=' * 80)


if __name__ == "__main__":
    test_simple_notice_query()
