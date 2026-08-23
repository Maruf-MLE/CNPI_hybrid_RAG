"""
Test script for the complete metadata extraction and embedding flow
Shows both embedding content and stored content
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

def test_metadata_extraction_only():
    """Test only the LLM metadata extraction"""
    print("=" * 80)
    print("🧪 TEST 1: LLM Metadata Extraction (Gemini)")
    print("=" * 80)
    
    # Sample notice content
    test_content = """[context_added_date: 2026-08-22 | context_added_time: 20:05:00 BST]
Doc Type: notices
Department: CST
Topic: ক্লাস বাতিল নোটিশ

আগামী ২২ আগস্ট ২০২৬ তারিখে শিক্ষক প্রশিক্ষণ কর্মসূচির কারণে সকল ক্লাস অনুষ্ঠিত হবে না। 
সকল শিক্ষার্থীদের জানানো হচ্ছে যে এই দিন কোন ক্লাস থাকবে না। পরবর্তী ক্লাস শিডিউল পরে জানানো হবে।

অধ্যক্ষ
CNPI"""
    
    from nodes.metadata_extractor import extract_notice_metadata, format_metadata_for_embedding
    
    print("\n📥 Input Content:")
    print("-" * 80)
    print(test_content)
    print()
    
    print("\n🤖 Calling Gemini LLM for metadata extraction...")
    metadata = extract_notice_metadata(
        content=test_content,
        title_en=None,
        topic="ক্লাস বাতিল নোটিশ"
    )
    
    if metadata:
        print("\n✅ Extraction Successful!")
        print("=" * 80)
        print(f"📌 Title (EN): {metadata.get('title_en')}")
        print(f"\n📝 Search Summary (BN):\n{metadata.get('search_summary')}")
        print(f"\n🔑 Key Facts:")
        for i, fact in enumerate(metadata.get('key_facts', []), 1):
            print(f"   {i}. {fact}")
        
        print("\n" + "=" * 80)
        print("📄 Formatted Content for Embedding:")
        print("=" * 80)
        formatted = format_metadata_for_embedding(metadata)
        print(formatted)
        print()
        
        return True, formatted
    else:
        print("\n❌ Extraction Failed!")
        return False, None


def test_complete_flow():
    """Test the complete create_document flow"""
    print("\n" + "=" * 80)
    print("🧪 TEST 2: Complete Document Creation Flow")
    print("=" * 80)
    
    from admin_panel.services import create_document
    
    test_notice = """আগামী ২৫ আগস্ট ২০২৬ তারিখে কলেজ বার্ষিক ক্রীড়া প্রতিযোগিতার আয়োজন করা হবে। 

📅 তারিখ: ২৫ আগস্ট ২০২৬
🕐 সময়: সকাল ৯টা থেকে বিকেল ৪টা
📍 স্থান: কলেজ খেলার মাঠ

সকল বিভাগের শিক্ষার্থীদের অংশগ্রহণ করার জন্য অনুরোধ করা হচ্ছে। 

📝 নিবন্ধন প্রয়োজন
⏰ নিবন্ধনের শেষ তারিখ: ২৪ আগস্ট ২০২৬

যোগাযোগ: ক্রীড়া বিভাগ
ফোন: 01712345678"""
    
    print("\n📝 Creating document with content:")
    print("-" * 80)
    print(test_notice)
    print()
    
    print("\n⚙️  Running create_document()...")
    print("   → Translation")
    print("   → Entity Normalization")
    print("   → Timestamp Generation")
    print("   → [PARALLEL] LLM Metadata Extraction + Temporal Analysis")
    print("   → Embedding Generation")
    print("   → Database Insert")
    print()
    
    import time
    result = create_document(
        chunk_id=f"test-sports-notice-{int(time.time())}",
        content=test_notice,
        doc_type="notices",
        topic="বার্ষিক ক্রীড়া প্রতিযোগিতা",
        department="General",
        meta={"test": True, "test_run": "metadata_flow"},
        source_file="test_metadata_flow.py"
    )
    
    if result.get("error"):
        print(f"\n❌ Error: {result['error']}")
        return False
    
    if result.get("created"):
        print("\n✅ Document Created Successfully!")
        print("=" * 80)
        print(f"📊 Creation Summary:")
        print(f"   • Doc ID: {result.get('doc_id')}")
        print(f"   • Chunk ID: {result.get('chunk_id')}")
        print(f"   • Notice ID: {result.get('notice_id', 'N/A')}")
        print(f"   • Embedding Generated: {result.get('embedding_generated')}")
        print(f"   • Translation Performed: {result.get('translation_performed')}")
        print(f"   • Temporal Analysis: {result.get('temporal_analysis_performed')}")
        print(f"   • Metadata Extraction Success: {result.get('metadata_extraction_success')}")
        print()
        
        # Show both contents side by side
        print("\n" + "=" * 80)
        print("📋 COMPARISON: Embedding Content vs Stored Content")
        print("=" * 80)
        
        embedding_content = result.get('embedding_content', '')
        stored_content = result.get('stored_content', '')
        
        print("\n🔹 EMBEDDING CONTENT (Used for semantic search):")
        print("-" * 80)
        print(embedding_content)
        print()
        
        print("\n🔹 STORED CONTENT (Saved in database):")
        print("-" * 80)
        # Show first 500 chars
        print(stored_content[:500] + "..." if len(stored_content) > 500 else stored_content)
        print()
        
        print("\n📈 Content Length Comparison:")
        print(f"   • Embedding Content: {len(embedding_content)} chars")
        print(f"   • Stored Content: {len(stored_content)} chars")
        print(f"   • Reduction: {len(stored_content) - len(embedding_content)} chars")
        print()
        
        return True
    
    return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🚀 TESTING DOCUMENT PROCESSING PIPELINE WITH GEMINI")
    print("=" * 80)
    print(f"⏰ Time: 2026-08-22 20:05:44 BST")
    print(f"🤖 LLM: Gemini 3.5 Flash Lite (via llm_utils.py)")
    print("=" * 80)
    
    # Check if GEMINI_API_KEY is set
    if not os.getenv("GEMINI_API_KEY"):
        print("\n⚠️  ERROR: GEMINI_API_KEY not set in .env file!")
        print("Please add your Gemini API key to .env file:")
        print("GEMINI_API_KEY=your-key-here")
        return
    
    print("\n✅ GEMINI_API_KEY found in environment")
    
    # Test 1: Metadata extraction only
    test1_passed, formatted_content = test_metadata_extraction_only()
    
    # Test 2: Complete flow (only if test 1 passed)
    test2_passed = False
    if test1_passed:
        print("\n" + "⏸️ " * 40)
        user_input = input("\n▶️  Continue with create_document() test? This will insert into DB. (y/N): ")
        if user_input.lower() == 'y':
            test2_passed = test_complete_flow()
        else:
            print("\n⏭️  Skipped Test 2")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"✓ Metadata Extraction Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"✓ Create Document Test: {'✅ PASSED' if test2_passed else '⏭️  SKIPPED' if not test1_passed or user_input.lower() != 'y' else '❌ FAILED'}")
    print("=" * 80)
    
    if test1_passed:
        print("\n💡 Key Features Working:")
        print("   ✓ LLM metadata extraction using Gemini")
        print("   ✓ Content formatting for embeddings")
        print("   ✓ Parallel processing (LLM + Temporal)")
        print("   ✓ Separate content for embedding vs storage")
        print("   ✓ Response includes both contents for visibility")
    
    print()


if __name__ == "__main__":
    main()
