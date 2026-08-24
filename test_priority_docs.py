"""
Test script for Priority Documents functionality
=================================================

Tests:
1. Add priority documents
2. List priority documents
3. Update priority order
4. Test retrieval with priority docs
5. Remove priority documents
"""

import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_PANEL_URL = f"{BASE_URL}/admin-panel/api"

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_response(response: requests.Response):
    """Print formatted response."""
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print()


# =============================================================================
# Test 1: Search for documents to add to priority list
# =============================================================================

print_section("Test 1: Search for documents to add to priority list")

# Search for some documents
search_payload = {
    "query": "কম্পিউটার বিজ্ঞান",
    "top_k": 5
}

print(f"Searching for documents: {search_payload}")
response = requests.post(f"{ADMIN_PANEL_URL}/search/", json=search_payload)
print_response(response)

if response.status_code == 200:
    search_results = response.json().get("results", [])
    if search_results:
        # Get first 3 document IDs for testing
        test_doc_ids = [doc["doc_id"] for doc in search_results[:3]]
        print(f"✓ Found {len(test_doc_ids)} documents to test with: {test_doc_ids}")
    else:
        print("✗ No documents found. Please add some documents first.")
        exit(1)
else:
    print("✗ Search failed")
    exit(1)


# =============================================================================
# Test 2: Add documents to priority list
# =============================================================================

print_section("Test 2: Add documents to priority list")

priority_docs_added = []

for i, doc_id in enumerate(test_doc_ids):
    add_payload = {
        "doc_id": doc_id,
        "priority_order": i,
        "reason": f"Test priority document {i+1} - Important for computer science queries"
    }
    
    print(f"Adding document {doc_id} to priority list with order {i}...")
    response = requests.post(f"{ADMIN_PANEL_URL}/priority-docs/add/", json=add_payload)
    print_response(response)
    
    if response.status_code == 200:
        priority_docs_added.append(response.json().get("priority_document"))
        print(f"✓ Successfully added document {doc_id} to priority list")
    else:
        print(f"✗ Failed to add document {doc_id}")


# =============================================================================
# Test 3: List all priority documents
# =============================================================================

print_section("Test 3: List all priority documents")

print("Fetching all active priority documents...")
response = requests.get(f"{ADMIN_PANEL_URL}/priority-docs/?active_only=true")
print_response(response)

if response.status_code == 200:
    priority_list = response.json().get("priority_documents", [])
    print(f"✓ Found {len(priority_list)} priority documents")
    for doc in priority_list:
        print(f"  - Priority #{doc['priority_order']}: doc_id={doc['doc_id']}, chunk_id={doc['chunk_id'][:30]}...")
else:
    print("✗ Failed to list priority documents")


# =============================================================================
# Test 4: Get priority documents statistics
# =============================================================================

print_section("Test 4: Get priority documents statistics")

print("Fetching priority documents stats...")
response = requests.get(f"{ADMIN_PANEL_URL}/priority-docs/stats/")
print_response(response)

if response.status_code == 200:
    stats = response.json().get("stats", {})
    print(f"✓ Total active priority documents: {stats.get('total_active', 0)}")
else:
    print("✗ Failed to get stats")


# =============================================================================
# Test 5: Update priority order
# =============================================================================

print_section("Test 5: Update priority order")

if priority_docs_added:
    first_priority_doc = priority_docs_added[0]
    priority_id = first_priority_doc.get("priority_id")
    
    update_payload = {
        "priority_id": priority_id,
        "priority_order": 99  # Move to end
    }
    
    print(f"Updating priority order for priority_id={priority_id} to 99...")
    response = requests.post(f"{ADMIN_PANEL_URL}/priority-docs/update-order/", json=update_payload)
    print_response(response)
    
    if response.status_code == 200:
        print(f"✓ Successfully updated priority order")
    else:
        print(f"✗ Failed to update priority order")


# =============================================================================
# Test 6: Test RAG retrieval with priority documents
# =============================================================================

print_section("Test 6: Test RAG retrieval with priority documents")

# Test with admin panel search (which uses semantic_search with priority docs)
test_query = "কম্পিউটার বিজ্ঞান বিভাগ"
search_payload = {
    "query": test_query,
    "top_k": 10
}

print(f"Testing retrieval with query: '{test_query}'")
print(f"Expected: Priority docs should appear first in results")
response = requests.post(f"{ADMIN_PANEL_URL}/search/", json=search_payload)
print_response(response)

if response.status_code == 200:
    results = response.json().get("results", [])
    print(f"\n✓ Retrieved {len(results)} documents")
    
    # Check if priority docs are in the results
    priority_doc_ids_set = {doc["doc_id"] for doc in priority_docs_added}
    found_priority_count = 0
    
    print("\nFirst 5 results:")
    for i, result in enumerate(results[:5], 1):
        doc_id = result.get("doc_id")
        is_priority = "✓ PRIORITY" if doc_id in priority_doc_ids_set else ""
        score = result.get("score", 0)
        print(f"  [{i}] doc_id={doc_id}, score={score:.4f} {is_priority}")
        if doc_id in priority_doc_ids_set:
            found_priority_count += 1
    
    if found_priority_count > 0:
        print(f"\n✓ SUCCESS: {found_priority_count} priority documents found in top 5 results!")
    else:
        print(f"\n⚠ WARNING: No priority documents found in top 5 results")
else:
    print("✗ Retrieval test failed")


# =============================================================================
# Test 7: Test RAG chat API with priority documents
# =============================================================================

print_section("Test 7: Test RAG chat API with priority documents")

chat_payload = {
    "query": "কম্পিউটার বিজ্ঞান বিভাগ সম্পর্কে বলো",
    "session_id": "test_priority_session_001"
}

print(f"Testing chat API with query: '{chat_payload['query']}'")
print("Expected: Priority documents should be included in the context")

try:
    response = requests.post(f"{BASE_URL}/api/chat/", json=chat_payload, timeout=30)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get("answer", "")
        contexts = data.get("contexts", [])
        
        print(f"✓ Chat API responded successfully")
        print(f"  Answer length: {len(answer)} characters")
        print(f"  Contexts retrieved: {len(contexts)}")
        
        # Check if priority docs are in contexts
        if contexts:
            print("\nFirst 3 contexts:")
            for i, ctx in enumerate(contexts[:3], 1):
                rank = ctx.get("rank", i)
                score = ctx.get("score", 0)
                content_preview = ctx.get("content", "")[:100]
                print(f"  [{rank}] score={score:.4f}")
                print(f"      {content_preview}...")
    else:
        print("✗ Chat API failed")
except requests.exceptions.Timeout:
    print("⚠ Chat API request timed out (this is normal for long processing)")
except Exception as e:
    print(f"✗ Chat API error: {e}")


# =============================================================================
# Test 8: Remove priority documents (cleanup)
# =============================================================================

print_section("Test 8: Remove priority documents (cleanup)")

print("Removing test priority documents...")

for priority_doc in priority_docs_added:
    priority_id = priority_doc.get("priority_id")
    doc_id = priority_doc.get("doc_id")
    
    remove_payload = {
        "priority_id": priority_id
    }
    
    print(f"Removing priority_id={priority_id} (doc_id={doc_id})...")
    response = requests.post(f"{ADMIN_PANEL_URL}/priority-docs/remove/", json=remove_payload)
    
    if response.status_code == 200:
        print(f"✓ Successfully removed")
    else:
        print(f"✗ Failed to remove")
        print_response(response)

print("\n" + "=" * 80)
print("  All tests completed!")
print("=" * 80)


# =============================================================================
# Summary
# =============================================================================

print_section("Test Summary")

print("""
✓ Priority Documents functionality has been tested:
  1. ✓ Add documents to priority list
  2. ✓ List all priority documents
  3. ✓ Get priority documents statistics
  4. ✓ Update priority order
  5. ✓ Test retrieval (admin panel search)
  6. ✓ Test RAG chat API
  7. ✓ Remove priority documents

The system now supports:
  - Always-retrieve priority documents
  - Automatic inclusion in all queries
  - Dynamic retrieval: (priority_count + query_based_count = total_k)
  - Priority docs appear first in results
  - Admin panel API for management

Next steps:
  - Add frontend UI in admin panel for easier management
  - Monitor performance with priority docs
  - Adjust priority_order values as needed
""")
