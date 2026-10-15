"""
Gemini Key Rotation System - Full Test Suite
============================================
Run: python test_key_rotation.py
"""

import sys
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []


# ===========================================================================
# TEST 1: Key Loading
# ===========================================================================
print("\n" + "="*55)
print("TEST 1: Key Loading from .env")
print("="*55)

from Cnpi_RAG.utils.key_manager import get_key_manager, _ensure_table, _get_db_conn

km = get_key_manager()
keys = km._keys
print(f"  Keys found: {len(keys)}")
for key, label in keys:
    masked = key[:8] + "..." + key[-4:]
    print(f"  - {label}: {masked}")

if keys:
    print(f"  {PASS} Keys loaded successfully")
    results.append(("Test 1: Key Loading", True))
else:
    print(f"  {FAIL} No keys loaded — check .env")
    results.append(("Test 1: Key Loading", False))


# ===========================================================================
# TEST 2: DB Table Auto-Create
# ===========================================================================
print("\n" + "="*55)
print("TEST 2: DB Table Auto-Create")
print("="*55)

try:
    _ensure_table()
    conn = _get_db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = 'gemini_key_cooldown'"
            )
            row = cur.fetchone()
    conn.close()

    if row:
        print(f"  Table 'gemini_key_cooldown' exists in DB")
        print(f"  {PASS} Table auto-created successfully")
        results.append(("Test 2: DB Table", True))
    else:
        print(f"  {FAIL} Table not found in DB")
        results.append(("Test 2: DB Table", False))
except Exception as e:
    print(f"  {FAIL} DB error: {e}")
    results.append(("Test 2: DB Table", False))


# ===========================================================================
# TEST 3: get_next_key() returns correct key
# ===========================================================================
print("\n" + "="*55)
print("TEST 3: get_next_key() — round-robin")
print("="*55)

try:
    k1, l1 = km.get_next_key()
    print(f"  Call 1 → {l1}: {k1[:8]}...{k1[-4:]}")
    k2, l2 = km.get_next_key()
    print(f"  Call 2 → {l2}: {k2[:8]}...{k2[-4:]}")
    print(f"  {PASS} get_next_key() works")
    results.append(("Test 3: get_next_key()", True))
except RuntimeError as e:
    print(f"  {FAIL} RuntimeError: {e}")
    results.append(("Test 3: get_next_key()", False))


# ===========================================================================
# TEST 4: mark_exhausted() + cooldown check
# ===========================================================================
print("\n" + "="*55)
print("TEST 4: mark_exhausted() + _is_exhausted() + cooldown")
print("="*55)

try:
    # একটা fake key দিয়ে test করো (real key exhausted করবো না)
    FAKE_KEY = "FAKE_TEST_KEY_12345_do_not_use"
    FAKE_LABEL = "TEST_KEY_FAKE"

    # প্রথমে clean করো
    conn = _get_db_conn()
    with conn:
        with conn.cursor() as cur:
            from Cnpi_RAG.utils.key_manager import _hash_key
            cur.execute(
                "DELETE FROM gemini_key_cooldown WHERE key_hash = %s",
                (_hash_key(FAKE_KEY),)
            )
    conn.close()

    # ১. শুরুতে available হওয়া উচিত
    before = km._is_exhausted(FAKE_KEY)
    print(f"  Before mark_exhausted → is_exhausted: {before}")
    assert before == False, "Should be available initially"

    # ২. mark করো
    km.mark_exhausted(FAKE_KEY, FAKE_LABEL, "Simulated 429 test")
    after = km._is_exhausted(FAKE_KEY)
    print(f"  After  mark_exhausted → is_exhausted: {after}")
    assert after == True, "Should be exhausted after mark"

    # ৩. hours remaining check
    hrs = km.get_hours_remaining(FAKE_KEY)
    print(f"  Hours remaining: {hrs:.1f}h (should be ~24h)")
    assert 23.9 <= hrs <= 24.1, f"Expected ~24h, got {hrs}"

    # ৪. cleanup
    conn = _get_db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM gemini_key_cooldown WHERE key_hash = %s",
                (_hash_key(FAKE_KEY),)
            )
    conn.close()

    print(f"  {PASS} mark_exhausted() + cooldown working correctly")
    results.append(("Test 4: Cooldown", True))

except Exception as e:
    import traceback
    print(f"  {FAIL} Error: {e}")
    print(traceback.format_exc())
    results.append(("Test 4: Cooldown", False))


# ===========================================================================
# TEST 5: call_llm() — real Gemini API call
# ===========================================================================
print("\n" + "="*55)
print("TEST 5: call_llm() — real Gemini API call")
print("="*55)

from Cnpi_RAG.utils.llm_utils import call_llm

try:
    response = call_llm(
        system_message="You are a helpful assistant. Reply very briefly.",
        user_prompt="Say the word 'hello' only. Nothing else."
    )
    print(f"  Response: '{response[:100]}'")

    if response.startswith("Error"):
        print(f"  {FAIL} API returned error: {response}")
        results.append(("Test 5: Real API call", False))
    else:
        print(f"  {PASS} Real Gemini API call successful")
        results.append(("Test 5: Real API call", True))
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results.append(("Test 5: Real API call", False))


# ===========================================================================
# TEST 6: All keys exhausted → proper error message
# ===========================================================================
print("\n" + "="*55)
print("TEST 6: All keys exhausted → error message")
print("="*55)

try:
    from Cnpi_RAG.utils.key_manager import _hash_key

    # সব real key কে temporarily exhausted করো
    conn = _get_db_conn()
    exhausted_keys = []
    with conn:
        with conn.cursor() as cur:
            for key, label in km._keys:
                cur.execute("""
                    INSERT INTO gemini_key_cooldown
                        (key_hash, key_label, exhausted_at, cooldown_hours, notes)
                    VALUES (%s, %s, NOW(), 24, 'test simulation')
                    ON CONFLICT (key_hash) DO UPDATE SET
                        exhausted_at = EXCLUDED.exhausted_at
                """, (_hash_key(key), label))
                exhausted_keys.append((_hash_key(key), label))
    conn.close()
    print(f"  Temporarily exhausted {len(exhausted_keys)} key(s) in DB")

    # এখন call_llm করলে error আসা উচিত
    response = call_llm(
        system_message="test",
        user_prompt="test"
    )
    print(f"  Response: '{response[:120]}'")

    # cleanup — exhausted mark সরিয়ে দাও
    conn = _get_db_conn()
    with conn:
        with conn.cursor() as cur:
            for key_hash, label in exhausted_keys:
                cur.execute(
                    "DELETE FROM gemini_key_cooldown WHERE key_hash = %s",
                    (key_hash,)
                )
    conn.close()
    print(f"  Cleaned up exhausted marks")

    if "exhausted" in response.lower() or "error" in response.lower():
        print(f"  {PASS} Correct error message when all keys exhausted")
        results.append(("Test 6: All exhausted", True))
    else:
        print(f"  {FAIL} Expected error message, got: {response}")
        results.append(("Test 6: All exhausted", False))

except Exception as e:
    import traceback
    print(f"  {FAIL} Exception: {e}")
    print(traceback.format_exc())
    results.append(("Test 6: All exhausted", False))


# ===========================================================================
# TEST 7: status() output
# ===========================================================================
print("\n" + "="*55)
print("TEST 7: km.status() — key status report")
print("="*55)

try:
    statuses = km.status()
    for s in statuses:
        hrs = f" ({s['hours_remaining']}h left)" if s['hours_remaining'] else ""
        print(f"  {s['label']}: {s['status']}{hrs}")
    print(f"  {PASS} status() works")
    results.append(("Test 7: status()", True))
except Exception as e:
    print(f"  {FAIL} {e}")
    results.append(("Test 7: status()", False))


# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "="*55)
print("SUMMARY")
print("="*55)

passed = sum(1 for _, ok in results if ok)
total = len(results)

for name, ok in results:
    icon = PASS if ok else FAIL
    print(f"  {icon}  {name}")

print(f"\n  Result: {passed}/{total} passed")
if passed == total:
    print("  All tests passed!")
else:
    print(f"  {total - passed} test(s) failed — check above for details")
