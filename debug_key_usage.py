"""
Debug: কোন key দিয়ে request যাচ্ছে দেখো
"""
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

from Cnpi_RAG.utils.key_manager import get_key_manager
from Cnpi_RAG.utils.llm_utils import call_llm, _make_llm
from langchain_core.messages import SystemMessage, HumanMessage

km = get_key_manager()
print(f"\nLoaded keys: {[l for _, l in km._keys]}")

# Monkey-patch _make_llm to log which key is used
import Cnpi_RAG.utils.llm_utils as llm_mod

_orig_make_llm = llm_mod._make_llm
def _patched_make_llm(api_key, model, temperature=None):
    # find label
    label = next((l for k, l in km._keys if k == api_key), api_key[:12]+'...')
    print(f"  >> _make_llm called with: {label}")
    return _orig_make_llm(api_key, model, temperature)
llm_mod._make_llm = _patched_make_llm

print("\n--- Request 1 ---")
r1 = call_llm("Reply in 1 word.", "Say: one")
print(f"Response: {r1}")

print("\n--- Request 2 ---")
r2 = call_llm("Reply in 1 word.", "Say: two")
print(f"Response: {r2}")

print("\n--- Request 3 ---")
r3 = call_llm("Reply in 1 word.", "Say: three")
print(f"Response: {r3}")

print("\nDone. If all 3 used KEY_1, rotation is correct (only switches on 429).")
