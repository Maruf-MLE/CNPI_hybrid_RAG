"""
Test Admin Panel Write Access (Simplified)
===========================================

Direct test of admin panel's ability to use write operations
without Django dependencies.
"""

import sys
from pathlib import Path

# Add Cnpi_RAG to path
project_root = Path(__file__).resolve().parent
cnpi_rag_root = project_root / "Cnpi_RAG"
sys.path.insert(0, str(cnpi_rag_root))

from utils.db_utils import get_db_connection, execute_query
from datetime import datetime


def test_read_with_write_flag():
    """Test that allow_write=True connection can read"""
    print("\n" + "="*60)
    print("TEST 1: Read with Write Connection (Should PASS)")
    print("="*60)
    
    try:
        conn = get_db_connection(allow_write=True)
        if not conn:
            print("❌ Failed to get connection")
            return False
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notices")
        count = cursor.fetchone()[0]
        conn.close()
        
        print(f"✅ Read operation successful with write connection")
        print(f"   Found {count} notices in database")
        return True
    except Exception as e:
        print(f"❌ Read failed: {e}")
        return False


def test_write_with_write_flag():
    """Test that allow_write=True connection can write"""
    print("\n" + "="*60)
    print("TEST 2: Write with Write Connection (Should PASS)")
    print("="*60)
    
    test_id = f"admin_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        conn = get_db_connection(allow_write=True)
        if not conn:
            print("❌ Failed to get connection")
            return False
        
        cursor = conn.cursor()
        
        # Try INSERT
        cursor.execute("""
            INSERT INTO documents (chunk_id, content, doc_type, embedding)
            VALUES (%s, %s, %s, ARRAY(SELECT random() FROM generate_series(1, 1024))::vector)
            RETURNING doc_id
        """, (test_id, "Admin security test document", "test"))
        
        doc_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"✅ INSERT operation successful")
        print(f"   Created document with doc_id: {doc_id}")
        
        # Try UPDATE
        cursor.execute("""
            UPDATE documents 
            SET content = %s 
            WHERE doc_id = %s
        """, ("Updated admin test document", doc_id))
        conn.commit()
        
        print(f"✅ UPDATE operation successful")
        print(f"   Updated document {doc_id}")
        
        # Clean up - DELETE
        cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
        conn.commit()
        conn.close()
        
        print(f"✅ DELETE operation successful (cleanup)")
        print(f"   Removed test document {doc_id}")
        
        return True
    except Exception as e:
        print(f"❌ Write operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_without_flag_blocked():
    """Test that default connection blocks writes"""
    print("\n" + "="*60)
    print("TEST 3: Write without Flag (Should FAIL)")
    print("="*60)
    
    try:
        # This should fail - no allow_write flag
        execute_query(
            "INSERT INTO documents (chunk_id, content) VALUES ('test', 'test')",
            fetch=False
        )
        print("❌ SECURITY BREACH: Write was allowed without flag!")
        return False
    except PermissionError as e:
        print(f"✅ Write correctly blocked without allow_write flag")
        print(f"   Error: {str(e)[:80]}...")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_simulated_admin_workflow():
    """Simulate typical admin panel workflow"""
    print("\n" + "="*60)
    print("TEST 4: Simulated Admin Panel Workflow (Should PASS)")
    print("="*60)
    
    test_chunk_id = f"workflow_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # Step 1: Admin connects with write permission
        conn = get_db_connection(allow_write=True)
        cursor = conn.cursor()
        
        # Step 2: Admin searches existing documents
        cursor.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'test'")
        before_count = cursor.fetchone()[0]
        print(f"   Step 1: Found {before_count} test documents")
        
        # Step 3: Admin creates new document
        cursor.execute("""
            INSERT INTO documents (chunk_id, content, doc_type, embedding)
            VALUES (%s, %s, %s, ARRAY(SELECT random() FROM generate_series(1, 1024))::vector)
            RETURNING doc_id, chunk_id
        """, (test_chunk_id, "Admin workflow test - initial content", "test"))
        
        result = cursor.fetchone()
        doc_id = result[0]
        chunk_id = result[1]
        conn.commit()
        print(f"   Step 2: Created document (doc_id={doc_id}, chunk_id={chunk_id})")
        
        # Step 4: Admin retrieves the document
        cursor.execute("SELECT content FROM documents WHERE doc_id = %s", (doc_id,))
        content = cursor.fetchone()[0]
        print(f"   Step 3: Retrieved document content: '{content[:40]}...'")
        
        # Step 5: Admin updates the document
        cursor.execute("""
            UPDATE documents 
            SET content = %s 
            WHERE doc_id = %s
        """, ("Admin workflow test - updated content after review", doc_id))
        conn.commit()
        print(f"   Step 4: Updated document content")
        
        # Step 6: Admin verifies the change
        cursor.execute("SELECT content FROM documents WHERE doc_id = %s", (doc_id,))
        updated_content = cursor.fetchone()[0]
        print(f"   Step 5: Verified update: '{updated_content[:40]}...'")
        
        # Cleanup
        cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
        conn.commit()
        conn.close()
        
        print(f"✅ Complete admin workflow executed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Admin workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("ADMIN PANEL WRITE ACCESS TEST SUITE")
    print("Verifying admin panel can perform all database operations")
    print("="*60)
    
    tests = [
        ("Read with write connection", test_read_with_write_flag),
        ("Write operations with flag", test_write_with_write_flag),
        ("Write blocked without flag", test_write_without_flag_blocked),
        ("Complete admin workflow", test_simulated_admin_workflow),
    ]
    
    results = []
    for test_name, test_func in tests:
        passed = test_func()
        results.append((test_name, passed))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for test_name, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All admin tests passed! Admin panel has full write access.")
        print("   Admin can: CREATE, READ, UPDATE, DELETE documents")
    else:
        print("⚠️  Some tests failed. Review admin panel configuration.")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
