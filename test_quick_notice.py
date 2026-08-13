"""
Quick Test for SQL Notice Path
================================

Direct test without Django server.
"""

import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "Cnpi_RAG"))
sys.path.insert(0, str(project_root / "plan"))

print("=" * 80)
print("SQL NOTICE PATH - QUICK TEST")
print("=" * 80)

# Test 1: Import modules
print("\n1. Testing imports...")
try:
    from nodes.sql_query_create import sql_query_create_node
    from nodes.context_format import context_format_node
    from nodes.router import llm_decide_path_node
    from utils.db_utils import execute_query, test_connection
    print("   ✓ All imports successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Database connection
print("\n2. Testing database connection...")
try:
    if test_connection():
        print("   ✓ Database connected")
    else:
        print("   ✗ Database connection failed")
except Exception as e:
    print(f"   ✗ Database error: {e}")

# Test 3: Check notices table
print("\n3. Checking notices table...")
try:
    results = execute_query(
        "SELECT COUNT(*) as cnt FROM notices WHERE institution_id = 1;",
        fetch=True
    )
    count = results[0]['cnt'] if results else 0
    print(f"   ✓ Found {count} notices in database")
    
    if count == 0:
        print("   ⚠ WARNING: No notices found. Add some notices to test properly.")
except Exception as e:
    print(f"   ✗ Query failed: {e}")

# Test 4: SQL Generation + Execution
print("\n4. Testing SQL query generation and execution...")
try:
    state = {
        "normalized_query": "latest notice dao",
        "user_input": "latest notice dao",
        "sql_query": {}
    }
    
    print("   Running sql_query_create_node...")
    result = sql_query_create_node(state)
    
    sql_state = result.get("sql_query", {})
    query_str = sql_state.get("query_str", "")
    row_count = sql_state.get("row_count", 0)
    contexts = sql_state.get("contexts", [])
    
    print(f"\n   Generated SQL:")
    print(f"   {query_str[:100]}..." if len(query_str) > 100 else f"   {query_str}")
    print(f"\n   ✓ Retrieved {row_count} row(s)")
    print(f"   ✓ Formatted {len(contexts)} context(s)")
    
    if contexts:
        print(f"\n   First notice:")
        ctx = contexts[0]
        print(f"   - Title: {ctx.get('title_bn', 'N/A')[:50]}...")
        print(f"   - Created: {ctx.get('created_at', 'N/A')}")
    else:
        print("   ⚠ No contexts returned")
        
except Exception as e:
    print(f"   ✗ Test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Context Formatting
print("\n5. Testing context formatting...")
try:
    if contexts:
        format_state = {
            "sql_query": result.get("sql_query", {})
        }
        
        format_result = context_format_node(format_state)
        sql_retrieve = format_result.get("sql_retrieve", {})
        formatted_context = sql_retrieve.get("context_with_meta", "")
        
        print(f"   ✓ Formatted context length: {len(formatted_context)} chars")
        print(f"\n   Preview:")
        print(f"   {formatted_context[:200]}...")
    else:
        print("   ⚠ Skipped (no contexts to format)")
        
except Exception as e:
    print(f"   ✗ Formatting failed: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("\n✅ If all tests passed, the SQL notice path is working!")
print("🚀 Next: Start Django server and test via API")
print("\nCommand: cd cnpi_api && python manage.py runserver")
