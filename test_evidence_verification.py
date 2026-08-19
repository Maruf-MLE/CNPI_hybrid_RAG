"""
Test Evidence Verification Node
=================================

This script tests the new evidence verification flow by simulating
a temporal reasoning scenario similar to the one described:

User Query: "আজকে কি উপবৃত্তি দেওয়া হবে?"
Current Date: 13 August 2026 (Thursday)
Context: Notice published on 12 August 2026 stating "উপবৃত্তি বৃহস্পতিবার প্রদান করা হবে।"

Expected:
- Evidence verification node should detect that:
  * Notice date = 12 August 2026
  * Event = Thursday
  * Current date = 13 August 2026 (Thursday)
  * Therefore, the event is scheduled for today
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root / "Cnpi_RAG") not in sys.path:
    sys.path.insert(0, str(project_root / "Cnpi_RAG"))
if str(project_root / "plan") not in sys.path:
    sys.path.insert(0, str(project_root / "plan"))

from Cnpi_RAG.nodes.evidence_verification import evidence_verification_node
import json


def test_temporal_reasoning():
    """Test temporal reasoning: Notice date vs Event date."""
    
    print("=" * 80)
    print("TEST 1: Temporal Reasoning - Notice Date vs Event Date")
    print("=" * 80)
    
    state = {
        "user_input": "আজকে কি উপবৃত্তি দেওয়া হবে?",
        "decided_path": "sql_retrieve",
        "sql_retrieve": {
            "context_with_meta": """Notice Date: 12 August 2026
Title: উপবৃত্তি বিতরণ
Content: উপবৃত্তি বৃহস্পতিবার প্রদান করা হবে।
Department: All
Priority: High
"""
        }
    }
    
    result = evidence_verification_node(state)
    verified_evidence = json.loads(result["sql_retrieve"]["verified_evidence"])
    
    print("\nUser Query:", state["user_input"])
    print("Current Date: 13 August 2026 (Thursday)")
    print("\nRetrieved Context:")
    print(state["sql_retrieve"]["context_with_meta"])
    
    print("\n" + "=" * 80)
    print("EVIDENCE VERIFICATION OUTPUT:")
    print("=" * 80)
    print(json.dumps(verified_evidence, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("KEY FINDINGS:")
    print("=" * 80)
    print(f"Intent: {verified_evidence.get('intent')}")
    print(f"Evidence Status: {verified_evidence.get('evidence_status')}")
    print(f"Answer Guidance: {verified_evidence.get('answer_guidance')}")
    
    if verified_evidence.get('temporal_analysis'):
        print("\nTemporal Analysis:")
        for item in verified_evidence['temporal_analysis']:
            print(f"  - {item}")
    
    print("\n✓ Test completed\n")


def test_entity_matching():
    """Test exact entity matching: Department + Semester + Shift."""
    
    print("=" * 80)
    print("TEST 2: Entity Matching - Department + Semester + Shift")
    print("=" * 80)
    
    state = {
        "user_input": "CST 5th semester 2nd Shift-এর captain কে?",
        "decided_path": "sql_query",
        "sql_query": {
            "optimized_context": """Department: CST
Semester: 5th
Shift: 1st Shift
Captain: MD Jakir Hossain
"""
        }
    }
    
    result = evidence_verification_node(state)
    verified_evidence = json.loads(result["sql_query"]["verified_evidence"])
    
    print("\nUser Query:", state["user_input"])
    print("\nRetrieved Context:")
    print(state["sql_query"]["optimized_context"])
    
    print("\n" + "=" * 80)
    print("EVIDENCE VERIFICATION OUTPUT:")
    print("=" * 80)
    print(json.dumps(verified_evidence, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("KEY FINDINGS:")
    print("=" * 80)
    print(f"Intent: {verified_evidence.get('intent')}")
    print(f"Evidence Status: {verified_evidence.get('evidence_status')}")
    
    if verified_evidence.get('conflicts'):
        print("\nConflicts Detected:")
        for conflict in verified_evidence['conflicts']:
            print(f"  - {conflict}")
    
    if verified_evidence.get('uncertainties'):
        print("\nUncertainties:")
        for uncertainty in verified_evidence['uncertainties']:
            print(f"  - {uncertainty}")
    
    print("\n✓ Test completed\n")


def test_negative_evidence():
    """Test negative evidence handling: Not mentioned vs Does not exist."""
    
    print("=" * 80)
    print("TEST 3: Negative Evidence - Not Mentioned vs Does Not Exist")
    print("=" * 80)
    
    state = {
        "user_input": "Library-তে AC আছে?",
        "decided_path": "sql_retrieve",
        "sql_retrieve": {
            "context_with_meta": """Facility: Library
Available: Books, Wi-Fi, Reading Room
Open Hours: 8:00 AM - 5:00 PM
"""
        }
    }
    
    result = evidence_verification_node(state)
    verified_evidence = json.loads(result["sql_retrieve"]["verified_evidence"])
    
    print("\nUser Query:", state["user_input"])
    print("\nRetrieved Context:")
    print(state["sql_retrieve"]["context_with_meta"])
    
    print("\n" + "=" * 80)
    print("EVIDENCE VERIFICATION OUTPUT:")
    print("=" * 80)
    print(json.dumps(verified_evidence, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("KEY FINDINGS:")
    print("=" * 80)
    print(f"Evidence Status: {verified_evidence.get('evidence_status')}")
    print(f"Answer Guidance: {verified_evidence.get('answer_guidance')}")
    
    print("\n✓ Test completed\n")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "EVIDENCE VERIFICATION NODE TESTS" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    try:
        test_temporal_reasoning()
        test_entity_matching()
        test_negative_evidence()
        
        print("=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
