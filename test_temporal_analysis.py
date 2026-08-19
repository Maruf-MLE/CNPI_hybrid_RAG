"""
Test script for temporal analysis integration
==============================================

Tests the complete document creation flow with temporal analysis:
1. Translation (if Bengali)
2. Entity normalization
3. Temporal analysis (NEW)
4. Timestamp + metadata prepending
5. Embedding generation
6. Database insertion

Usage:
    cd G:\CNPI_Hybrid_RAG
    python test_temporal_analysis.py
"""

import os
import sys
from pathlib import Path

# Add Cnpi_RAG to path
project_root = Path(__file__).resolve().parent
cnpi_rag_root = project_root / "Cnpi_RAG"
sys.path.insert(0, str(cnpi_rag_root))
sys.path.insert(0, str(project_root / "cnpi_api"))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("  Temporal Analysis Integration Test")
print("=" * 70)
print()

# Test 1: Direct temporal analyzer test
print("[Test 1] Testing temporal_analyzer.py directly...")
print("-" * 70)

from nodes.temporal_analyzer import analyze_temporal_context

test_content_1 = """
আগামীকাল ক্লাস বন্ধ থাকবে। 
পরীক্ষা ১৫ আগস্ট থেকে ২০ আগস্ট পর্যন্ত চলবে।
সকল শিক্ষার্থীদের উপস্থিত থাকতে হবে।
"""

print(f"Content: {test_content_1.strip()}")
print()
print("Calling analyze_temporal_context()...")

result_1 = analyze_temporal_context(test_content_1, notice_date="2026-08-14")

print("\nResult:")
import json
print(json.dumps(result_1, indent=2, ensure_ascii=False))
print()

# Test 2: Test with ongoing information
print("\n[Test 2] Testing with ONGOING information...")
print("-" * 70)

test_content_2 = """
CNPI-তে নতুন Software Lab চালু করা হয়েছে।
এই ল্যাবে ৩০টি কম্পিউটার এবং আধুনিক সুবিধা রয়েছে।
"""

print(f"Content: {test_content_2.strip()}")
print()

result_2 = analyze_temporal_context(test_content_2, notice_date="2026-08-14")

print("\nResult:")
print(json.dumps(result_2, indent=2, ensure_ascii=False))
print()

# Test 3: Test full integration through admin panel services
print("\n[Test 3] Testing full integration through services.create_document()...")
print("-" * 70)

# Import admin panel services
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cnpi_api.settings")
sys.path.insert(0, str(project_root / "cnpi_api"))

try:
    import django
    django.setup()
    print("Django setup successful")
except Exception as e:
    print(f"Django setup skipped: {e}")

# Now import services
from admin_panel.services import create_document

test_chunk_id = f"test_temporal_{int(os.urandom(4).hex(), 16)}"
test_content_3 = """
আগামীকাল সকাল ৯টায় CST বিভাগে একটি গুরুত্বপূর্ণ সভা অনুষ্ঠিত হবে।
সকল শিক্ষক এবং CI-দের উপস্থিত থাকতে অনুরোধ করা হচ্ছে।
"""

print(f"Chunk ID: {test_chunk_id}")
print(f"Content (Bengali): {test_content_3.strip()}")
print()
print("Calling services.create_document()...")
print("This will:")
print("  1. Detect Bengali and translate to English")
print("  2. Normalize entities (CST, CI, etc.)")
print("  3. Run temporal analysis (extract 'আগামীকাল', '৯টায়', etc.)")
print("  4. Add timestamp metadata")
print("  5. Generate embedding")
print("  6. Insert into documents table with temporal_analysis column")
print()

result_3 = create_document(
    chunk_id=test_chunk_id,
    content=test_content_3,
    doc_type="announcement",
    topic="Department Meeting",
    department="CST",
    meta={"test": True},
    source_file="test_temporal_analysis.py"
)

print("\nResult:")
print(json.dumps(result_3, indent=2, ensure_ascii=False))
print()

if "error" in result_3:
    print(f"❌ Error: {result_3['error']}")
else:
    print("✅ Document created successfully!")
    print(f"   doc_id: {result_3.get('doc_id')}")
    print(f"   Translation performed: {result_3.get('translation_performed')}")
    print(f"   Temporal analysis performed: {result_3.get('temporal_analysis_performed')}")
    
    # Show the final content structure
    if result_3.get('document'):
        doc = result_3['document']
        print("\n--- Final Document Content Preview ---")
        content = doc.get('content', '')
        preview = content[:500] + "..." if len(content) > 500 else content
        print(preview)

print()
print("=" * 70)
print("  Test Complete!")
print("=" * 70)
