import sys
from pathlib import Path

current_dir = Path.cwd()
sys.path.insert(0, str(current_dir / 'plan'))
sys.path.insert(0, str(current_dir / 'Cnpi_RAG'))

from Cnpi_RAG.nodes.sql_query_info_check import sql_query_info_check_node

print("=" * 80)
print("Testing Updated sql_query_info_check with ROUTINE queries")
print("=" * 80)

# Test case 1: The exact query you mentioned - should detect missing semester
test_cases = [
    {
        "name": "Test 1: CST Day Shift routine (semester missing)",
        "query": "Where can I find the class Routine for the CST Department Day Shift?",
        "expected": {
            "short_info": True,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": True,
        }
    },
    {
        "name": "Test 2: CST Day Shift 5th semester routine (all present)",
        "query": "Where can I find the class Routine for the CST Department Day Shift 5th semester?",
        "expected": {
            "short_info": False,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": False,
        }
    },
    {
        "name": "Test 3: Just 'class routine' (all missing)",
        "query": "class routine dao",
        "expected": {
            "short_info": True,
            "missing_shift": True,
            "missing_department": True,
            "missing_semester": True,
        }
    },
    {
        "name": "Test 4: CST Day Shift CI (no semester needed)",
        "query": "Who is the Chief Instructor of CST Day Shift?",
        "expected": {
            "short_info": False,
            "missing_shift": False,
            "missing_department": False,
            "missing_semester": False,
        }
    },
    {
        "name": "Test 5: CST department CI (shift missing, no semester needed)",
        "query": "Who is the Chief Instructor of CST department?",
        "expected": {
            "short_info": True,
            "missing_shift": True,
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
        'sql_query': {}
    }
    
    result = sql_query_info_check_node(state)
    sql_state = result.get('sql_query', {})
    
    # Check results
    actual = {
        "short_info": sql_state.get("short_info"),
        "missing_shift": sql_state.get("missing_shift"),
        "missing_department": sql_state.get("missing_department"),
        "missing_semester": sql_state.get("missing_semester"),
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
        if actual.get(key) != test['expected'][key]:
            passed = False
            print(f"  ❌ MISMATCH on {key}: expected {test['expected'][key]}, got {actual.get(key)}")
    
    if passed:
        print("\n✅ TEST PASSED")
    else:
        print("\n❌ TEST FAILED")
    
    # Show clarification if any
    if sql_state.get("short_info"):
        clarification = sql_state.get("final_answer", "")
        print(f"\nClarification message:")
        print(f"  {clarification}")

print(f"\n{'='*80}")
print("All tests completed!")
print(f"{'='*80}")
