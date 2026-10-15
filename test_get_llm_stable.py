"""
Test get_llm() — nodes যেভাবে call করে সেটা simulate করো
যাচাই: একই key বারবার ব্যবহার হয়, key rotate হয় না
"""
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()

from Cnpi_RAG.utils.key_manager import get_key_manager
from Cnpi_RAG.utils.llm_utils import get_llm, _get_llm_cache
from langchain_core.messages import SystemMessage, HumanMessage

km = get_key_manager()
print(f"Keys: {[l for _, l in km._keys]}")

used_keys = []

print("\n--- Simulating 5 node calls (get_llm() style) ---")
for i in range(5):
    llm = get_llm()   # node এর মতো করে
    # কোন api_key এর instance সেটা cache থেকে বের করো
    for (model, temp, api_key), inst in _get_llm_cache.items():
        if inst is llm:
            label = next((l for k, l in km._keys if k == api_key), api_key[:8])
            used_keys.append(label)
            print(f"  Call {i+1} → {label}")
            break

all_same = len(set(used_keys)) == 1
print(f"\nAll same key: {all_same}")
print("[PASS] get_llm() always returns same key" if all_same else "[FAIL] get_llm() is rotating keys — should NOT!")
