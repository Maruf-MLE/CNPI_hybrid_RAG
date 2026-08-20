"""
Test script to test captain query with full information
"""
import sys
from pathlib import Path

# Add paths
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "plan"))
sys.path.insert(0, str(current_dir / "Cnpi_RAG"))

from Cnpi_RAG.graph import app
from plan.state import new_rag_state

def test_queries():
    print("=" * 60)
    print("Testing Multiple Captain Queries")
    print("=" * 60)
    
    # Compile graph
    print("\n[1] Compiling graph...")
    try:
        compiled_graph = app.compile()
        print("✓ Graph compiled successfully\n")
    except Exception as e:
        print(f"✗ Error compiling graph: {e}")
        return
    
    # Test queries with varying levels of detail
    test_cases = [
        "class captain ke?",
        "CST er class captain ke?",
        "5th semester er class captain ke?",
        "CST 5th semester er class captain ke?",
        "CST 2nd shift 5th semester er class captain ke?",
        "Computer Technology 2nd shift 5th semester captain phone number",
    ]
    
    for idx, query in enumerate(test_cases, 1):
        print("\n" + "=" * 60)
        print(f"Test {idx}: '{query}'")
        print("=" * 60)
        
        # Create initial state
        initial_state = new_rag_state(
            user_input=query,
            messages=[],
        )
        
        try:
            # Execute graph
            result_state = compiled_graph.invoke(initial_state)
            
            # Print key information
            print(f"✓ Decided Path: {result_state.get('decided_path')}")
            print(f"✓ Confidence: {result_state.get('confidence_score')}")
            
            # Check SQL Query state
            if result_state.get('decided_path') == 'sql_query':
                sql_query_state = result_state.get('sql_query', {})
                print(f"✓ short_info: {sql_query_state.get('short_info')}")
                print(f"✓ missing_department: {sql_query_state.get('missing_department')}")
                print(f"✓ missing_shift: {sql_query_state.get('missing_shift')}")
                print(f"✓ missing_semester: {sql_query_state.get('missing_semester')}")
                
                # Print final answer
                final_ans = result_state.get("final_answer", "") or sql_query_state.get("final_answer", "")
                print(f"\n📝 Answer: {final_ans[:100]}...")
            else:
                print(f"⚠ Went to {result_state.get('decided_path')} instead of sql_query")
                
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_queries()
