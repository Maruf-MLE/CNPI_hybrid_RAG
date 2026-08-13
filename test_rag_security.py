"""
Test RAG System Read-Only Security
===================================

This script tests that the RAG system cannot execute write operations.
"""

import sys
from pathlib import Path

# Add Cnpi_RAG to path
project_root = Path(__file__).resolve().parent
cnpi_rag_root = project_root / "Cnpi_RAG"
sys.path.insert(0, str(cnpi_rag_root))

from utils.db_utils import execute_query


def test_select_allowed():
    """Test that SELECT queries work in RAG system"""
    print("\n" + "="*60)
    print("TEST 1: SELECT Query (Should PASS)")
    print("="*60)
    
    try:
        result = execute_query(
            "SELECT notice_id, title_bn FROM notices LIMIT 1",
            fetch=True
        )
        print(f"✅ SELECT query executed successfully")
        print(f"   Retrieved {len(result)} row(s)")
        if result:
            print(f"   Sample data: notice_id={result[0].get('notice_id')}")
        return True
    except Exception as e:
        print(f"❌ SELECT query failed: {e}")
        return False


def test_insert_blocked():
    """Test that INSERT queries are blocked"""
    print("\n" + "="*60)
    print("TEST 2: INSERT Query (Should FAIL)")
    print("="*60)
    
    try:
        execute_query(
            """INSERT INTO notices (institution_id, title_bn, content_bn) 
               VALUES (1, 'Test', 'Test Content')""",
            fetch=False
        )
        print("❌ SECURITY BREACH: INSERT was allowed!")
        return False
    except PermissionError as e:
        print(f"✅ INSERT correctly blocked")
        print(f"   Error: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_update_blocked():
    """Test that UPDATE queries are blocked"""
    print("\n" + "="*60)
    print("TEST 3: UPDATE Query (Should FAIL)")
    print("="*60)
    
    try:
        execute_query(
            "UPDATE notices SET title_bn = 'Hacked' WHERE notice_id = 1",
            fetch=False
        )
        print("❌ SECURITY BREACH: UPDATE was allowed!")
        return False
    except PermissionError as e:
        print(f"✅ UPDATE correctly blocked")
        print(f"   Error: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_delete_blocked():
    """Test that DELETE queries are blocked"""
    print("\n" + "="*60)
    print("TEST 4: DELETE Query (Should FAIL)")
    print("="*60)
    
    try:
        execute_query(
            "DELETE FROM notices WHERE notice_id = 999",
            fetch=False
        )
        print("❌ SECURITY BREACH: DELETE was allowed!")
        return False
    except PermissionError as e:
        print(f"✅ DELETE correctly blocked")
        print(f"   Error: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_drop_blocked():
    """Test that DROP queries are blocked"""
    print("\n" + "="*60)
    print("TEST 5: DROP Query (Should FAIL)")
    print("="*60)
    
    try:
        execute_query(
            "DROP TABLE notices",
            fetch=False
        )
        print("❌ SECURITY BREACH: DROP was allowed!")
        return False
    except PermissionError as e:
        print(f"✅ DROP correctly blocked")
        print(f"   Error: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_sql_injection_blocked():
    """Test that SQL injection attempts are blocked"""
    print("\n" + "="*60)
    print("TEST 6: SQL Injection Attempt (Should FAIL)")
    print("="*60)
    
    try:
        # Attempt to inject DELETE after SELECT
        execute_query(
            "SELECT * FROM notices WHERE notice_id = 1; DELETE FROM notices WHERE 1=1",
            fetch=True
        )
        print("❌ SECURITY BREACH: SQL injection was allowed!")
        return False
    except PermissionError as e:
        print(f"✅ SQL injection correctly blocked")
        print(f"   Error: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("RAG SYSTEM SECURITY TEST SUITE")
    print("Testing read-only enforcement on database operations")
    print("="*60)
    
    tests = [
        ("SELECT allowed", test_select_allowed),
        ("INSERT blocked", test_insert_blocked),
        ("UPDATE blocked", test_update_blocked),
        ("DELETE blocked", test_delete_blocked),
        ("DROP blocked", test_drop_blocked),
        ("SQL injection blocked", test_sql_injection_blocked),
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
        print("🎉 All security tests passed! RAG system is read-only.")
    else:
        print("⚠️  Some tests failed. Review security implementation.")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
