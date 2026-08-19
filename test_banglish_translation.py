"""
Test Banglish Detection and Translation
========================================

Tests the updated doc_translator to detect and translate Banglish.

Usage:
    cd G:\CNPI_Hybrid_RAG
    python test_banglish_translation.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "Cnpi_RAG"))

from dotenv import load_dotenv
load_dotenv()

from nodes.doc_translator import translate_to_english, _contains_bengali, _is_banglish, _should_translate

print("=" * 70)
print("  Banglish Detection & Translation Test")
print("=" * 70)
print()

# Test cases
test_cases = [
    {
        "name": "Pure Banglish",
        "input": "ajke class hobe na",
        "expected_detect": True
    },
    {
        "name": "Banglish with English words",
        "input": "ajke CST department e class hobe na",
        "expected_detect": True
    },
    {
        "name": "Bengali Unicode",
        "input": "আজকে ক্লাস হবে না",
        "expected_detect": True
    },
    {
        "name": "Mixed (Bengali + Banglish)",
        "input": "আজকে class hobe na",
        "expected_detect": True
    },
    {
        "name": "Pure English",
        "input": "There will be no class today",
        "expected_detect": False
    },
    {
        "name": "Banglish Notice",
        "input": "agamikal porikha hobe. shobai present thakben.",
        "expected_detect": True
    },
    {
        "name": "Common Banglish phrases",
        "input": "tumi kothay jabe? ami asbo kal.",
        "expected_detect": True
    },
]

print("Testing Detection...")
print("-" * 70)

for i, test in enumerate(test_cases, 1):
    input_text = test["input"]
    expected = test["expected_detect"]
    
    has_bengali = _contains_bengali(input_text)
    is_banglish = _is_banglish(input_text)
    should_translate = _should_translate(input_text)
    
    status = "✅" if should_translate == expected else "❌"
    
    print(f"\n[Test {i}] {test['name']}")
    print(f"  Input: {input_text}")
    print(f"  Has Bengali Unicode: {has_bengali}")
    print(f"  Is Banglish: {is_banglish}")
    print(f"  Should Translate: {should_translate} (Expected: {expected}) {status}")

print("\n" + "=" * 70)
print("  Translation Test")
print("=" * 70)

# Test actual translation
translation_tests = [
    "ajke class hobe na",
    "ajke CST department e meeting hobe",
    "agamikal porikha. shobai present thakben",
]

for i, text in enumerate(translation_tests, 1):
    print(f"\n[Translation {i}]")
    print(f"  Input (Banglish): {text}")
    print(f"  Translating...")
    
    try:
        translated = translate_to_english(text)
        print(f"  Output (English): {translated}")
        print(f"  Status: ✅ Translation successful")
    except Exception as e:
        print(f"  Status: ❌ Translation failed: {e}")

print("\n" + "=" * 70)
print("  Test Complete!")
print("=" * 70)
