import sys
from pathlib import Path

current_dir = Path.cwd()
sys.path.insert(0, str(current_dir / 'plan'))
sys.path.insert(0, str(current_dir / 'Cnpi_RAG'))

from Cnpi_RAG.nodes.sql_retrieve_check import sql_retrieve_check_node

print("=" * 80)
print("Testing sql_retrieve_check with ROUTINE queries")
print("=" * 80)

# Test case 1: The exact query - should detect missing semester
test_cases = [
    {
        "name": "Test 1: CST Day Shift routine (semester missing)",
        "query": "Where can I find the class Routine for the CST Department Day Shift?",
        "expected": {
            "need_more_info": True,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": True,
        }
    },
    {
        "name": "Test 2: CST Day Shift 5th semester routine (all present)",
        "query": "Where can I find the class Routine for the CST Department Day Shift 5th semester?",
        "expected": {
            "need_more_info": False,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": False,
        }
    },
    {
        "name": "Test 3: Just 'class routine' (all missing)",
        "query": "class routine dao",
        "expected": {
            "need_more_info": True,
            "missing_shift": True,
            "missing_department": True,
            "missing_semester": True,
        }
    },
    {
        "name": "Test 4: CST Day Shift CI (no semester needed)",
        "query": "Who is the Chief Instructor of CST Day Shift?",
        "expected": {
            "need_more_info": False,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": False,
        }
    },
]

for test in test_cases:
    print(f"\n{'='*80}")
    print(f"{test['name']}")
    print(f"Query: {test['query']}")
    print(f"{'='*80}")
    
    state = {
        'user_input': test['query'],
        'normalized_query': test['query'],
        'sql_retrieve': {}
    }
    
    result = sql_retrieve_check_node(state)
    sql_retrieve_state = result.get('sql_retrieve', {})
    sql_query_state = result.get('sql_query', {})
    
    # Check results
    actual = {
        "need_more_info": sql_retrieve_state.get("need_more_info"),
        "missing_shift": sql_query_state.get("missing_shift"),
        "missing_department": sql_query_state.get("missing_department"),
        "missing_semester": sql_query_state.get("missing_semester"),
    }
    
    print(f"\nExpected:")
    for key, value in test['expected'].items():
        print(f"  {key}: {value}")
    
    print(f"\nActual:")
    for key, value in actual.items():
        print(f"  {key}: {value}")
    
    # Check if test passed
    passed = True
    for key in test['expected']:
        expected_val = test['expected'][key]
        actual_val = actual.get(key)
        # Handle None vs False comparison
        if expected_val == False and actual_val is None:
            actual_val = False
        if actual_val != expected_val:
            passed = False
            print(f"  ❌ MISMATCH on {key}: expected {expected_val}, got {actual_val}")
    
    if passed:
        print("\n✅ TEST PASSED")
    else:
        print("\n❌ TEST FAILED")
    
    # Show clarification if any
    if sql_retrieve_state.get("need_more_info"):
        clarification = sql_retrieve_state.get("final_answer", "")
        print(f"\nClarification message:")
        print(f"  {clarification}")

print(f"\n{'='*80}")
print("All tests completed!")
print(f"{'='*80}")
