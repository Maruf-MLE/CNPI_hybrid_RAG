"""
Test script for the new LLM metadata extraction and embedding flow
"""

import sys
from pathlib import Path

# Add Cnpi_RAG to path
_CNPI_RAG_ROOT = Path(__file__).resolve().parent / "Cnpi_RAG"
if str(_CNPI_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(_CNPI_RAG_ROOT))

# Add cnpi_api to path
_CNPI_API_ROOT = Path(__file__).resolve().parent / "cnpi_api"
if str(_CNPI_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_CNPI_API_ROOT))

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_metadata_extraction():
    """Test LLM metadata extraction function"""
    print("=" * 70)
    print("Testing LLM Metadata Extraction")
    print("=" * 70)
    
    # Sample notice content
    test_content = """[context_added_date: 2026-08-22 | context_added_time: 19:58:00 BST]
Doc Type: notices
Department: CST
Topic: ক্লাস বাতিল নোটিশ

আগামী ২২ আগস্ট ২০২৬ তারিখে শিক্ষক প্রশিক্ষণ কর্মসূচির কারণে সকল ক্লাস অনুষ্ঠিত হবে না। সকল শিক্ষার্থীদের জানানো হচ্ছে যে এই দিন কোন ক্লাস থাকবে না।

অধ্যক্ষ
CNPI"""
    
    from nodes.metadata_extractor import extract_notice_metadata, format_metadata_for_embedding
    
    print("\n📥 Input Content:")
    print("-" * 70)
    print(test_content)
    print()
    
    print("\n🤖 Calling LLM for metadata extraction...")
    metadata = extract_notice_metadata(
        content=test_content,
        title_en=None,
        topic="ক্লাস বাতিল নোটিশ"
    )
    
    if metadata:
        print("\n✅ Extraction Successful!")
        print("-" * 70)
        print(f"Title (EN): {metadata.get('title_en')}")
        print(f"\nSearch Summary (BN):\n{metadata.get('search_summary')}")
        print(f"\nKey Facts:")
        for i, fact in enumerate(metadata.get('key_facts', []), 1):
            print(f"  {i}. {fact}")
        
        print("\n" + "=" * 70)
        print("Formatted Content for Embedding:")
        print("=" * 70)
        formatted = format_metadata_for_embedding(metadata)
        print(formatted)
        print()
        
        return True
    else:
        print("\n❌ Extraction Failed!")
        return False


def test_create_document():
    """Test the complete create_document flow"""
    print("\n" + "=" * 70)
    print("Testing Complete create_document() Flow")
    print("=" * 70)
    
    from admin_panel.services import create_document
    
    test_notice = """আগামী ২৫ আগস্ট ২০২৬ তারিখে কলেজ বার্ষিক ক্রীড়া প্রতিযোগিতার আয়োজন করা হবে। সকল বিভাগের শিক্ষার্থীদের অংশগ্রহণ করার জন্য অনুরোধ করা হচ্ছে। প্রতিযোগিতা সকাল ৯টা থেকে বিকেল ৪টা পর্যন্ত চলবে।

নিবন্ধনের শেষ তারিখ: ২৪ আগস্ট ২০২৬
স্থান: কলেজ খেলার মাঠ
যোগাযোগ: ক্রীড়া বিভাগ"""
    
    print("\n📝 Creating document with content:")
    print("-" * 70)
    print(test_notice)
    print()
    
    print("\n⚙️  Running create_document()...")
    result = create_document(
        chunk_id="test-notice-sports-2026",
        content=test_notice,
        doc_type="notices",
        topic="বার্ষিক ক্রীড়া প্রতিযোগিতা",
        department="General",
        meta={"test": True},
        source_file="test_script"
    )
    
    if result.get("error"):
        print(f"\n❌ Error: {result['error']}")
        return False
    
    if result.get("created"):
        print("\n✅ Document Created Successfully!")
        print("-" * 70)
        print(f"Doc ID: {result.get('doc_id')}")
        print(f"Chunk ID: {result.get('chunk_id')}")
        print(f"Notice ID: {result.get('notice_id', 'N/A')}")
        print(f"Embedding Generated: {result.get('embedding_generated')}")
        print(f"Translation Performed: {result.get('translation_performed')}")
        print(f"Temporal Analysis: {result.get('temporal_analysis_performed')}")
        print(f"Metadata Extraction: {result['document']['meta'].get('metadata_extraction_success', False)}")
        print()
        
        # Show stored content (first 300 chars)
        stored_content = result['document'].get('content', '')
        print("\n📄 Stored Content (first 300 chars):")
        print("-" * 70)
        print(stored_content[:300] + "..." if len(stored_content) > 300 else stored_content)
        print()
        
        return True
    
    return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 Testing New Document Processing Pipeline")
    print("=" * 70)
    
    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("\n⚠️  WARNING: OPENAI_API_KEY not set in .env file!")
        print("Please add your OpenAI API key to .env file:")
        print("OPENAI_API_KEY=sk-...")
        print("\nSkipping tests that require OpenAI API.")
        return
    
    # Test 1: Metadata extraction only
    test1_passed = test_metadata_extraction()
    
    # Test 2: Complete flow (only if test 1 passed)
    test2_passed = False
    if test1_passed:
        print("\n" + "⏳" * 35)
        input("\nPress Enter to continue with create_document() test (will insert into DB)...")
        test2_passed = test_create_document()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"Metadata Extraction Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Create Document Test: {'✅ PASSED' if test2_passed else '⏭️  SKIPPED' if not test1_passed else '❌ FAILED'}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
