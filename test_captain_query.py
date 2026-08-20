"""
Test Captain Query
==================
Test if captain information is being retrieved correctly.
"""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "plan"))
sys.path.insert(0, str(current_dir / "Cnpi_RAG"))

from Cnpi_RAG.nodes.sql_query_create import sql_query_create_node
from Cnpi_RAG.nodes.sql_query_db_call import sql_query_db_call_node

def test_captain_query():
    print("=" * 80)
    print("TESTING: Captain Query")
    print("=" * 80)
    
    # Test queries
    queries = [
        "CST 2nd shift 5th semester er captain ke",
        "CST department er captain",
        "captain ke"
    ]
    
    for query in queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        state = {
            "user_input": query,
            "normalized_query": query,
            "sql_query": {}
        }
        
        print("\n[STEP 1] Generating SQL...")
        result1 = sql_query_create_node(state)
        sql_state = result1.get("sql_query", {})
        
        query_str = sql_state.get('query_str', '')
        if query_str:
            print(f"Generated SQL:\n{query_str[:200]}...")
        else:
            print("❌ No SQL generated")
            continue
        
        # Update state
        state = {**state, **result1}
        
        print("\n[STEP 2] Executing SQL...")
        result2 = sql_query_db_call_node(state)
        sql_state2 = result2.get("sql_query", {})
        
        row_count = sql_state2.get('row_count', 0)
        print(f"Row count: {row_count}")
        
        if row_count > 0:
            print(f"✅ Found {row_count} captain(s)")
            contexts = sql_state2.get('contexts', [])
            for i, ctx in enumerate(contexts[:3], 1):  # Show first 3
                print(f"\n  Captain {i}:")
                # Try different possible field names
                name = ctx.get('captain_name') or ctx.get('name') or 'N/A'
                dept = ctx.get('department') or 'N/A'
                shift = ctx.get('shift') or 'N/A'
                sem = ctx.get('semester') or 'N/A'
                phone = ctx.get('phone') or 'N/A'
                print(f"    Name: {name}")
                print(f"    Dept: {dept}, Shift: {shift}, Semester: {sem}")
                print(f"    Phone: {phone}")
        else:
            print("❌ No captain data found")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_captain_query()
