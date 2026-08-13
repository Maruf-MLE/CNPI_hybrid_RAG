"""
Test SQL Query Path for Notices
================================

This script tests the complete SQL query flow for notice retrieval:
1. Entry → Rewrite Query
2. Router → Decides sql_query path
3. Info Check → Validates query
4. SQL Query Create → Generates SQL
5. DB Call → Executes SQL
6. Response → Formats answer

Usage:
    python test_sql_notice_query.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "Cnpi_RAG"))
sys.path.insert(0, str(project_root / "plan"))

from Cnpi_RAG.nodes.entry import rewrite_query_node
from Cnpi_RAG.nodes.router import llm_decide_path_node
from Cnpi_RAG.nodes.sql_query_info_check import sql_query_info_check_node
from Cnpi_RAG.nodes.sql_query_create import sql_query_create_node
from Cnpi_RAG.nodes.sql_query_db_call import sql_query_db_call_node
from Cnpi_RAG.nodes.sql_query_response import sql_query_response_node


def test_sql_notice_path(user_query: str):
    """Test the complete SQL notice query path."""
    
    print("=" * 80)
    print(f"Testing SQL Notice Query Path")
    print("=" * 80)
    print(f"\n📝 User Query: {user_query}\n")
    
    # Initialize state
    state = {
        "user_input": user_query,
        "messages": [],
        "sql_query": {}
    }
    
    # Step 1: Rewrite Query
    print("🔄 Step 1: Rewriting query...")
    result = rewrite_query_node(state)
    state.update(result)
    print(f"   ✅ Rewritten: {state.get('rewritten_query')}\n")
    
    # Step 2: Router Decision
    print("🔀 Step 2: Routing decision...")
    result = llm_decide_path_node(state)
    state.update(result)
    decided_path = state.get("decided_path")
    confidence = state.get("confidence_score", 0.0)
    print(f"   ✅ Path: {decided_path} (confidence: {confidence:.2f})\n")
    
    if decided_path != "sql_query":
        print(f"   ⚠️  WARNING: Router chose '{decided_path}' instead of 'sql_query'")
        print(f"   This query might not be recognized as a notice query.\n")
        return
    
    # Step 3: Info Check
    print("🔍 Step 3: Checking query information...")
    result = sql_query_info_check_node(state)
    state.update(result)
    sql_query_state = state.get("sql_query", {})
    short_info = sql_query_state.get("short_info", False)
    not_possible = sql_query_state.get("not_possible", False)
    
    if short_info:
        print(f"   ⚠️  Insufficient info: {sql_query_state.get('final_answer')}\n")
        return
    if not_possible:
        print(f"   ❌ Not possible: {sql_query_state.get('final_answer')}\n")
        return
    
    print(f"   ✅ Query validated successfully\n")
    
    # Step 4: Generate SQL Query
    print("⚙️  Step 4: Generating SQL query...")
    result = sql_query_create_node(state)
    state.update(result)
    sql_query_state = state.get("sql_query", {})
    sql_query = sql_query_state.get("query_str", "")
    
    if not sql_query:
        print(f"   ❌ Failed to generate SQL query\n")
        return
    
    print(f"   ✅ Generated SQL:")
    print(f"\n{'-' * 80}")
    print(sql_query)
    print(f"{'-' * 80}\n")
    
    # Step 5: Execute SQL Query
    print("💾 Step 5: Executing SQL query...")
    result = sql_query_db_call_node(state)
    state.update(result)
    sql_query_state = state.get("sql_query", {})
    row_count = sql_query_state.get("row_count", 0)
    raw_context = sql_query_state.get("raw_context", "")
    
    print(f"   ✅ Retrieved {row_count} row(s)\n")
    
    if row_count == 0:
        print("   ⚠️  No data found in database\n")
        return
    
    print(f"   📊 Raw Database Result:")
    print(f"\n{'-' * 80}")
    print(raw_context[:500] + ("..." if len(raw_context) > 500 else ""))
    print(f"{'-' * 80}\n")
    
    # Step 6: Generate Response
    print("💬 Step 6: Generating final response...")
    result = sql_query_response_node(state)
    state.update(result)
    sql_query_state = state.get("sql_query", {})
    final_answer = sql_query_state.get("final_answer", "")
    
    print(f"   ✅ Response generated\n")
    
    # Display Final Answer
    print("=" * 80)
    print("📢 FINAL ANSWER")
    print("=" * 80)
    print(f"\n{final_answer}\n")
    print("=" * 80)


def main():
    """Run multiple test cases."""
    
    test_cases = [
        "latest notice dao",
        "সর্বশেষ নোটিশ দেখাও",
        "CNPI er last 5 notices",
        "শেষ ৫টি নোটিশ",
        "last notice",
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n\n{'#' * 80}")
        print(f"TEST CASE {i}/{len(test_cases)}")
        print(f"{'#' * 80}\n")
        
        try:
            test_sql_notice_path(query)
        except Exception as e:
            print(f"\n❌ ERROR: {e}\n")
            import traceback
            traceback.print_exc()
        
        if i < len(test_cases):
            print(f"\n{'─' * 80}\n")
            input("Press Enter to continue to next test case...")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                   SQL NOTICE QUERY PATH TEST SUITE                         ║
║                                                                            ║
║  This script tests the complete flow for notice queries:                  ║
║  User Query → Router → Info Check → SQL Generation → DB Call → Response   ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
    except Exception as e:
        print(f"\n\n❌ CRITICAL ERROR: {e}\n")
        import traceback
        traceback.print_exc()
