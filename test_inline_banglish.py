"""
Quick Banglish Test - Inline
=============================
Tests Banglish detection directly.
"""

# Test the detection logic inline
text = "ajke class hobe na"

# Check for Banglish keywords
banglish_words = ['ajke', 'hobe', 'na', 'korbo', 'jabe', 'dao', 'koro', 'kal']
found_words = [word for word in banglish_words if word in text.lower()]

print("=" * 60)
print("  Banglish Detection Test")
print("  Time: 2026-08-15 11:21 UTC (17:21 BST)")
print("=" * 60)
print()
print(f"Input: '{text}'")
print(f"Found Banglish words: {found_words}")
print(f"Should translate: {len(found_words) > 0}")
print()

if len(found_words) > 0:
    print("✅ DETECTION WORKING - Banglish detected!")
    print(f"   Found {len(found_words)} Banglish indicators")
else:
    print("❌ DETECTION FAILED - No Banglish found")

print()
print("=" * 60)
