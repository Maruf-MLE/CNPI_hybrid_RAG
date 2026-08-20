"""
Quick test for specific captain query clarification
"""
import sys
from pathlib import Path

# Add paths
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "plan"))
sys.path.insert(0, str(current_dir / "Cnpi_RAG"))

from Cnpi_RAG.graph import app
from plan.state import new_rag_state

def test_single_query():
    print("=" * 60)
    print("Testing: '5th semester er class captain ke'")
    print("=" * 60)
    
    # Compile graph
    print("\n[1] Compiling graph...")
    compiled_graph = app.compile()
    print("✓ Graph compiled\n")
    
    # Test query
    query = "5th semester er class captain ke"
    
    initial_state = new_rag_state(
        user_input=query,
        messages=[],
    )
    
    print(f"[2] Testing query: '{query}'\n")
    
    try:
        result_state = compiled_graph.invoke(initial_state)
        
        print("=" * 60)
        print("RESULT:")
        print("=" * 60)
        
        decided_path = result_state.get('decided_path')
        print(f"✓ Path: {decided_path}")
        print(f"✓ Confidence: {result_state.get('confidence_score')}")
        
        if decided_path == 'sql_query':
            sql_state = result_state.get('sql_query', {})
            print(f"\n[SQL Query State]")
            print(f"  short_info: {sql_state.get('short_info')}")
            print(f"  missing_department: {sql_state.get('missing_department')}")
            print(f"  missing_shift: {sql_state.get('missing_shift')}")
            print(f"  missing_semester: {sql_state.get('missing_semester')}")
            
            final_ans = sql_state.get("final_answer", "")
            print(f"\n{'='*60}")
            print("CLARIFICATION MESSAGE:")
            print('='*60)
            print(final_ans)
            print('='*60)
            
            # Check if it contains "Class Captain"
            if "Class Captain" in final_ans or "captain" in final_ans.lower():
                print("\n✅ SUCCESS: Clarification mentions Captain!")
            else:
                print("\n❌ FAILED: Clarification does NOT mention Captain")
                
        else:
            print(f"\n⚠️ Went to {decided_path} instead of sql_query")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_query()
