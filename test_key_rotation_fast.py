"""
Test key rotation — Tests 1,2,3,4,6 (no real API call for speed)
Run: python test_key_rotation_fast.py
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []

from Cnpi_RAG.utils.key_manager import (
    get_key_manager, _ensure_table, _get_db_conn, _hash_key
)

km = get_key_manager()

# ─── TEST 1: Key Loading ───────────────────────────────────────────────────
print("\n=== TEST 1: Key Loading ===")
for k, l in km._keys:
    print(f"  {l}: {k[:8]}...{k[-4:]}")
ok1 = len(km._keys) > 0
print(f"  {PASS if ok1 else FAIL}")
results.append(("Test 1: Key Loading", ok1))


# ─── TEST 2: DB Table ─────────────────────────────────────────────────────
print("\n=== TEST 2: DB Table Auto-Create ===")
_ensure_table()
conn = _get_db_conn()
with conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = %s",
            ("gemini_key_cooldown",)
        )
        row = cur.fetchone()
conn.close()
ok2 = row is not None
print(f"  Table exists: {ok2}")
print(f"  {PASS if ok2 else FAIL}")
results.append(("Test 2: DB Table", ok2))


# ─── TEST 3: get_next_key() ───────────────────────────────────────────────
print("\n=== TEST 3: get_next_key() round-robin ===")
try:
    k1, l1 = km.get_next_key()
    print(f"  Call 1 → {l1}")
    k2, l2 = km.get_next_key()
    print(f"  Call 2 → {l2}")
    ok3 = True
    print(f"  {PASS}")
except RuntimeError as e:
    print(f"  RuntimeError: {e}")
    ok3 = False
    print(f"  {FAIL}")
results.append(("Test 3: get_next_key()", ok3))


# ─── TEST 4: mark_exhausted + cooldown ────────────────────────────────────
print("\n=== TEST 4: mark_exhausted() + _is_exhausted() + hours_remaining ===")
FAKE = "TOTALLY_FAKE_KEY_FOR_TESTING_ONLY_9999"
FAKE_LABEL = "FAKE_TEST_KEY"

# cleanup before
conn = _get_db_conn()
with conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gemini_key_cooldown WHERE key_hash = %s", (_hash_key(FAKE),))
conn.close()

before = km._is_exhausted(FAKE)
km.mark_exhausted(FAKE, FAKE_LABEL, "Simulated 429 for unit test")
after  = km._is_exhausted(FAKE)
hrs    = km.get_hours_remaining(FAKE)

# cleanup after
conn = _get_db_conn()
with conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gemini_key_cooldown WHERE key_hash = %s", (_hash_key(FAKE),))
conn.close()

print(f"  Before mark → is_exhausted: {before}  (expect False)")
print(f"  After  mark → is_exhausted: {after}   (expect True)")
print(f"  Hours remaining: {hrs:.2f}h           (expect ~24.00)")

ok4 = (before == False) and (after == True) and (23.9 <= hrs <= 24.1)
print(f"  {PASS if ok4 else FAIL}")
results.append(("Test 4: Cooldown", ok4))


# ─── TEST 5: All keys exhausted → correct error ────────────────────────────
print("\n=== TEST 5: All keys exhausted → error message ===")
try:
    conn = _get_db_conn()
    marked_hashes = []
    with conn:
        with conn.cursor() as cur:
            for key, label in km._keys:
                h = _hash_key(key)
                cur.execute(
                    "INSERT INTO gemini_key_cooldown "
                    "(key_hash, key_label, exhausted_at, cooldown_hours, notes) "
                    "VALUES (%s, %s, NOW(), 24, %s) "
                    "ON CONFLICT (key_hash) DO UPDATE SET "
                    "exhausted_at = EXCLUDED.exhausted_at",
                    (h, label, "test simulation")
                )
                marked_hashes.append(h)
    conn.close()
    print(f"  Marked {len(marked_hashes)} key(s) as exhausted in DB")

    from Cnpi_RAG.utils.llm_utils import call_llm
    resp = call_llm("test", "test")
    print(f"  call_llm() response: '{resp[:120]}'")

    # cleanup
    conn = _get_db_conn()
    with conn:
        with conn.cursor() as cur:
            for h in marked_hashes:
                cur.execute("DELETE FROM gemini_key_cooldown WHERE key_hash = %s", (h,))
    conn.close()
    print("  Cleanup done")

    ok5 = "error" in resp.lower() or "exhausted" in resp.lower()
    print(f"  {PASS if ok5 else FAIL}")
    results.append(("Test 5: All exhausted", ok5))

except Exception as e:
    import traceback
    print(f"  Exception: {e}")
    traceback.print_exc()
    results.append(("Test 5: All exhausted", False))


# ─── TEST 6: status() report ────────────────────────────────────────────────
print("\n=== TEST 6: km.status() report ===")
try:
    statuses = km.status()
    for s in statuses:
        hrs_str = f"  ({s['hours_remaining']}h left)" if s['hours_remaining'] else ""
        print(f"  {s['label']}: {s['status']}{hrs_str}")
    ok6 = isinstance(statuses, list) and len(statuses) > 0
    print(f"  {PASS if ok6 else FAIL}")
    results.append(("Test 6: status()", ok6))
except Exception as e:
    print(f"  Exception: {e}")
    results.append(("Test 6: status()", False))


# ─── SUMMARY ───────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("SUMMARY")
print("="*50)
passed = sum(1 for _, ok in results if ok)
total  = len(results)
for name, ok in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"\n  {passed}/{total} passed")
