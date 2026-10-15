"""
Test real Gemini API call via call_llm()
Run: python test_api_call.py
"""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

print("Testing real Gemini API call...")

from Cnpi_RAG.utils.llm_utils import call_llm, call_llm_with_history
from langchain_core.messages import HumanMessage, AIMessage

# Test 1: basic call
print("\n=== TEST: call_llm() ===")
resp = call_llm(
    system_message="You are a helpful assistant. Reply very briefly in 1-2 words.",
    user_prompt="Say 'hello' only."
)
print(f"Response: '{resp}'")
print("[PASS]" if not resp.startswith("Error") else "[FAIL]")

# Test 2: call_llm_with_history
print("\n=== TEST: call_llm_with_history() ===")
history = []
answer, history = call_llm_with_history(
    system_message="You are a helpful assistant.",
    user_prompt="My name is Maruf. Just say OK.",
    chat_history=history
)
print(f"Turn 1: '{answer[:60]}'")
answer2, history = call_llm_with_history(
    system_message="You are a helpful assistant.",
    user_prompt="What is my name? One word answer.",
    chat_history=history
)
print(f"Turn 2 (should include 'Maruf'): '{answer2[:60]}'")
ok = "maruf" in answer2.lower() and not answer2.startswith("Error")
print("[PASS]" if ok else "[FAIL] (check if name remembered)")
