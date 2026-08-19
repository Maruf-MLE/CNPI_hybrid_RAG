"""
Quick Banglish Detection Test (No LLM)
======================================

Tests only the detection logic without calling LLM.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "Cnpi_RAG"))

from nodes.doc_translator import _contains_bengali, _is_banglish, _should_translate

print("=" * 70)
print("  Banglish Detection Test (Quick)")
print("  Current Time: 2026-08-15 17:18 BST")
print("=" * 70)
print()

test_cases = [
    ("ajke class hobe na", True, "Pure Banglish"),
    ("ajke CST e meeting hobe", True, "Banglish + English"),
    ("আজকে ক্লাস হবে না", True, "Bengali Unicode"),
    ("There will be no class today", False, "Pure English"),
    ("tumi kothay jabe", True, "Banglish question"),
    ("agamikal porikha hobe", True, "Banglish with -hobe ending"),
    ("The meeting is tomorrow", False, "Pure English"),
    ("class korbo ajke", True, "Banglish mixed"),
]

print("Testing Detection Logic:")
print("-" * 70)

for text, expected, desc in test_cases:
    has_bengali = _contains_bengali(text)
    is_banglish = _is_banglish(text)
    should_translate = _should_translate(text)
    
    status = "✅ PASS" if should_translate == expected else "❌ FAIL"
    
    print(f"\n{desc}")
    print(f"  Input: '{text}'")
    print(f"  Bengali Unicode: {has_bengali}")
    print(f"  Is Banglish: {is_banglish}")
    print(f"  Should Translate: {should_translate} (Expected: {expected})")
    print(f"  {status}")

print("\n" + "=" * 70)
print("  Detection Test Complete!")
print("=" * 70)
