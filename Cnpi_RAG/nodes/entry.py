"""
Entry Node - Phase 1
====================

This node handles the initial user input and prepares the query for routing.

Flow: user_input -> rewritten_query
"""

import sys
from pathlib import Path

# Ensure plan/ is importable so we can use the canonical state types
project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState                       # canonical state schema
from utils.llm_utils import get_llm, extract_content             # shared LLM singleton + helper
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage


rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system", '''You are a Query Rewrite Engine for the CNPI (Chapainawabganj Polytechnic Institute) RAG System.

Your task: Rewrite the user's question into clear English WITHOUT changing its meaning.

Context & Abbreviations:
- CNPI = Chapainawabganj Polytechnic Institute (Bangladesh)
- CI = Chief Instructor
- CST = Computer Science and Technology
- ET, ENT, RAC, MT, FT = Engineering departments
- Shift terminology: "2nd shift" = "Day shift" = "দ্বিতীয় শিফট" (they are the SAME thing)
- Shift terminology: "1st shift" = "Morning shift" = "প্রথম শিফট" (they are the SAME thing)

CRITICAL RULES:
1. Do NOT add extra information, assumptions, or scenarios
2. Do NOT interpret "ba" (বা/or) as alternative conditions - it just means the user is clarifying the same thing
3. Do NOT create complex conditional statements like "when X is not available"
4. ONLY translate and clean up the query - nothing more. BUT pronoun/reference resolution (see below) is MANDATORY and is NOT "adding extra information".

Examples:
✅ CORRECT:
- "cst 2nd shift ba day shift er ci ke" → "Who is the Chief Instructor of the CST 2nd shift?"
- "CST department er ci" → "Who is the Chief Instructor of the CST department?"
- "rejuanul sir er phone number" → "What is the phone number of Rejuanul sir?"

❌ WRONG (Over-interpretation):
- "cst 2nd shift ba day shift er ci ke" → "Who is the CI of 2nd shift when day shift CI is not available?" (NO!)
- "CST department er ci" → "Who is the primary CI of CST if no shift is specified?" (NO!)

Remember: "ba" (or) in Bengali queries usually means the user is clarifying alternate names for the SAME thing, NOT asking about alternatives.

--- CONVERSATION HISTORY (PRONOUN RESOLUTION - MANDATORY) ---
You will be given prior conversation messages (Chat History) before the current query.

You MUST use that history to resolve ALL pronouns and references in the current query so the rewritten query is FULLY self-contained.

Pronouns/references to resolve:
- Bengali: "তার", "তাহার", "ওনার", "onar", "tar", "tahar", "oi", "ওই", "এর", "তিনি", "tini"
- English: "he", "she", "his", "her", "their", "that", "this", "it"

Resolution rules:
1. Find the ENTITY (person name, department, shift, etc.) the pronoun refers to from the chat history.
2. REPLACE the pronoun with the full entity name in the rewritten query.
3. The rewritten query MUST be fully self-contained — someone with NO access to the history should understand exactly what is being asked and ABOUT WHOM.

Examples of pronoun resolution:
- History: User asked "CST Day Shift er CI ke?" → AI answered "Chief Instructor is Md: Jewel Rana Sir."
  Current: "onar phone number dao"
  ✅ CORRECT: "What is the phone number of Md: Jewel Rana Sir, the Chief Instructor of the CST Day Shift?"
  ❌ WRONG: "What is his phone number?" (pronoun NOT resolved)

- History: User asked about "ET department 1st shift"
  Current: "oi department er teacher ra ke"
  ✅ CORRECT: "Who are the teachers of the ET department 1st shift?"
  ❌ WRONG: "Who are the teachers of that department?" (pronoun NOT resolved)

- History: User asked about "Rejuanul sir"
  Current: "tar basa kothai"
  ✅ CORRECT: "Where does Rejuanul sir live?"
  ❌ WRONG: "Where is his home?" (pronoun NOT resolved)

If the current query does NOT contain any pronouns or references, just translate and clean it up normally.

Output: Only the clean, simple, self-contained English translation.'''),
    ("placeholder", "{chat_history}"),
    ("human", "Original Query: {user_input}")
])


def rewrite_query_node(state: RAGState) -> dict:
    """Rewrite user query for better retrieval.

    The full conversation history (``state["messages"]``) is injected into
    the prompt so the LLM can resolve pronouns / references from prior
    turns (e.g.  "তার ফোন নম্বর?" → whose?).  The current user query is
    still the last human message.
    """
    llm = get_llm()
    rewrite_chain = rewrite_prompt | llm

    user_input = state.get("normalized_query") or state.get("user_input", "")

    if not user_input:
        return {"rewritten_query": "Please enter your question first."}

    # ★ Chat history স্টেট থেকে নিয়ে প্রম্পটে পাঠানো হচ্ছে।
    # শেষ মেসেজটি হলো বর্তমান user_input (new_rag_state এ append করা),
    # তাই সেটি বাদ দিয়ে আগের ইতিহাস নিই।
    all_messages: list[BaseMessage] = state.get("messages", [])
    chat_history = all_messages[:-1] if all_messages else []

    try:
        response = rewrite_chain.invoke({
            "user_input": user_input,
            "chat_history": chat_history,
        })
        return {"rewritten_query": extract_content(response).strip()}
    except Exception as e:
        print(f"Rewrite error: {e}")
        return {"rewritten_query": user_input}


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "user_input": "What is the principal's full name?"
    }

    result = rewrite_query_node(state)
    print("Rewritten Query:")
    print(result)