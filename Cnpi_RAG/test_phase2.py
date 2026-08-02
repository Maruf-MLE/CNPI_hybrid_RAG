"""
Phase 2 SQL Query Path Test
============================

Test all 7 SQL Query nodes with sample queries.
"""

import os
from nodes.sql_query_info_check import sql_query_info_check_node
from nodes.sql_query_create import sql_query_create_node
from nodes.sql_query_db_call import sql_query_db_call_node
from nodes.sql_query_row_check_optimized import sql_query_row_check_and_optimize_node
from nodes.sql_query_response import sql_query_response_node
from nodes.sql_query_support_check import sql_query_support_check_node

test_queries = [
    "What is the head of Computer Science department?",
    "Who is the student advisor?",
    "List all department names",
    "What notices were published?",
]

def run_test(query, step):
    """Run single test step."""
    print(f"\n{'='*60}")
    print(f"TEST: {query}")
    print(f"Step: {step}")
    print('='*60)

if __name__ == "__main__":
    # Set environment variable
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "your-api-key-here")
    os.environ["DB_HOST"] = os.getenv("DB_HOST", "localhost")
    os.environ["DB_NAME"] = "college"
    os.environ["DB_USER"] = "postgres"
    os.environ["DB_PASSWORD"] = "postgres"
    os.environ["DB_PORT"] = "5432"

    for query in test_queries:
        print(f"\n{'#'*70}")
        print(f" RUNNING: {query}")
        print('#'*70)

        # Step 1: Info Check
        state = {"user_input": query, "sql_query": {}}
        result = sql_query_info_check_node(state)
        print(f"\nSQL Info Check:")
        print(f"  short_info: {result['sql_query'].get('short_info')}")
        print(f"  not_possible: {result['sql_query'].get('not_possible')}")
        print(f"  final_answer (if any): {result['sql_query'].get('final_answer', '')[:100]}...")

        if result['sql_query'].get('short_info') or result['sql_query'].get('not_possible'):
            print(f"\n❌ Query not suitable for SQL processing")
            continue

        # Step 2: SQL Create
        result = sql_query_create_node(result)
        print(f"\nSQL Generation:")
        print(f"  query_str: {result['sql_query'].get('query_str', '')[:100]}...")

        if not result['sql_query'].get('query_str'):
            print(f"\n⚠️ No SQL query generated")
            continue

        # Step 3: DB Call
        state = result
        result = sql_query_db_call_node(state)
        print(f"\nDatabase Query:")
        print(f"  row_count: {result['sql_query'].get('row_count')}")
        print(f"  raw_context (first 200 chars): {result['sql_query'].get('raw_context', '')[:200]}...")

        if result['sql_query'].get('row_count', 0) == 0:
            print(f"\n⚠️ No rows returned - SQL Retrieve would be better")
            continue

        # Step 4: Row Check & Optimize
        state = result
        result = sql_query_row_check_and_optimize_node(state)
        print(f"\nRow Check & Optimization:")
        print(f"  row_count: {result['sql_query'].get('row_count')}")
        print(f"  optimized_context (first 200 chars): {result['sql_query'].get('optimized_context', '')[:200]}...")

        # Step 5: Response Generation
        state = result
        state["user_query"] = query
        result = sql_query_response_node(state)
        print(f"\nResponse Generation:")
        print(f"  final_answer: {result['sql_query'].get('final_answer', '')[:200]}...")

        # Step 6: Support Check
        state = result
        result = sql_query_support_check_node(state)
        print(f"\nSupport Validation:")
        print(f"  answer_status: {result['sql_query'].get('answer_status')}")

        print(f"\n✅ SUCCESS: Full SQL Query Path completed")
        print('-'*70)

    print("\n\n#"*70)
    print("ALL TESTS COMPLETED")
    print('#'*70)