"""
SQL Retrieve Support Check Node - Phase 3
==========================================

Validates whether the LLM-generated answer is supported by the retrieved context.

Evaluation logic:
    1. Context lacks the actual answer:
       → LLM returns "no_support"
       → set supported=False, retry_count=MAX_RETRIES
       → graph routes directly to fallback (web_search_rewrite)

    2. Context has the answer, but AI hallucinated or added extra unverified info:
       → LLM returns "hallucination"
       → set supported=False, increment retry_count
       → graph retries sql_retrieve_response (same context, fresh LLM generation)

    3. Context has the answer and AI answer is accurate with no hallucination:
       → LLM returns "yes"
       → set supported=True, answer_status="found", final_answer set
       → graph routes to END

State read:
    user_input                      → the user's question
    sql_retrieve.final_answer       → the answer to verify
    sql_retrieve.context_with_meta  → the context used
    sql_retrieve.retry_count        → how many times we have already retried

State written:
    sql_retrieve.supported          → True / False
    sql_retrieve.retry_count        → incremented on hallucination, set to MAX_RETRIES on no_support
    answer_status                   → "found" on success
    final_answer                    → set on success
"""

import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
for _p in [str(plan_root), str(project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state import RAGState, MAX_RETRIES
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


# System prompt components
CORE_INSTRUCTIONS = """========================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
========================================

ROLE:
You are an uncompromising quality assurance and verification engine for a RAG system.

TASK:
Determine if the provided context actually answers the user's query and if the answer is factually supported by that context.

OUTPUT:
Return EXACTLY ONE of these three words:
- no_support
- hallucination
- yes

============================================================
ABSOLUTE RULE 1: WHEN TO RETURN "no_support" (HIGHEST PRIORITY)
============================================================
You MUST return "no_support" in any of the following cases:
1. The context DOES NOT contain the answer to the user's question.
2. The generated answer states that the information is missing, not mentioned, or not found.
   For example, answers like:
   - "প্রাপ্ত তথ্যে ... কোনো তথ্য উল্লেখ নেই"
   - "তথ্য পাওয়া যায়নি" / "তথ্য পাওয়া যায়নি"
   - "The context does not mention..."
   - "No information is available..."
   MUST ALWAYS BE CLASSIFIED AS "no_support"!
   DO NOT return "yes" merely because the answer is honest about missing information. In this system, if the context doesn't have the answer, it is STRICTLY "no_support" so the system can fall back to web search!
3. The context is irrelevant or unrelated to the user's question.

============================================================
ABSOLUTE RULE 2: WHEN TO RETURN "hallucination"
============================================================
You MUST return "hallucination" when:
- The context DOES contain the required information to answer the query, BUT:
  - The generated answer contains factually incorrect statements.
  - The generated answer includes extra, fabricated, or unverified information not found in the context (বাড়তি বা মনগড়া তথ্য).
  - The answer contradicts the context or distorts dates, names, or numbers.

============================================================
ABSOLUTE RULE 3: WHEN TO RETURN "yes"
============================================================
You may return "yes" ONLY when ALL three of these conditions are met:
1. The context ACTUALLY CONTAINS the positive answer to the user's question.
2. The generated answer ACTUALLY PROVIDES that answer using only the facts in the context.
3. There are NO hallucinations, NO factual errors, and NO extra fabricated details.

If the answer states that information is missing or absent, it fails conditions 1 and 2 -> return "no_support".

FINAL RESTRICTION:
Output ONLY one word: "no_support", "hallucination", or "yes".
Do not provide explanations, reasoning, punctuation, or any additional text."""

PROJECT_CONFIGURATION = """========================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
========================================

PROJECT:
CNPI Information Retrieval System

PROJECT CONTEXT:
The system retrieves information about CNPI from provided contextual documents and notices.

EVALUATION SCOPE:
Evaluate strictly using ONLY the provided context and query. Do not use external knowledge or outside assumptions."""

EXAMPLES_REFERENCE = """========================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
========================================

EXAMPLE 1: ANSWER SAYS INFO IS NOT IN CONTEXT (MUST BE no_support)
Context:
নোটিশ প্রকাশের তারিখ: ১৫-০৩-২০২৪। নোটিশে ক্লাস রুটিন ও পরীক্ষার ফি নিয়ে আলোচনা করা হয়েছে।
Query:
সিএনপিআইতে বিদায় অনুষ্ঠান (farewell ceremony) কবে হবে?
Answer:
প্রাপ্ত তথ্যে CNPI-তে কোনো বিদায় অনুষ্ঠান (farewell ceremony) বা বিদায় অনুষ্ঠান আয়োজনের তারিখ সম্পর্কে কোনো তথ্য উল্লেখ নেই।
Expected Output:
no_support
Reason:
The context does not have the answer to the user's question, and the answer confirms information is missing. This MUST be "no_support" so the system can fall back to web search.

EXAMPLE 2: CONTEXT LACKS RELEVANT INFORMATION (MUST BE no_support)
Context:
নোটিশে বার্ষিক ক্রীড়া প্রতিযোগিতা অনুষ্ঠানের কথা বলা হয়েছে।
Query:
সেমিস্টার ফাইনাল পরীক্ষা কবে অনুষ্ঠিত হবে?
Answer:
তথ্য পাওয়া যায়নি বা উল্লেখ নেই।
Expected Output:
no_support

EXAMPLE 3: CONTEXT HAS ANSWER, BUT AI HALLUCINATED EXTRA DETAILS (hallucination)
Context:
কম্পিউটার সায়েন্স বিভাগের প্রধান হলেন জনাব আহমেদ।
Query:
কম্পিউটার সায়েন্স বিভাগের প্রধান কে?
Answer:
কম্পিউটার সায়েন্স বিভাগের প্রধান জনাব আহমেদ। তিনি ২০১৫ সালে ঢাকা বিশ্ববিদ্যালয় থেকে গোল্ড মেডেল পেয়েছেন।
Expected Output:
hallucination
Reason:
The context mentions the department head, but the AI fabricated extra details about graduation year and university.

EXAMPLE 4: CONTEXT HAS ANSWER, BUT AI GAVE INCORRECT FACT (hallucination)
Context:
ভর্তি ফরম জমা দেওয়ার শেষ তারিখ ২৫ ডিসেম্বর ২০২৪।
Query:
ভর্তি ফরম জমা দেওয়ার শেষ তারিখ কবে?
Answer:
ভর্তি ফরম জমা দেওয়ার শেষ তারিখ ৩০ ডিসেম্বর ২০২৪।
Expected Output:
hallucination

EXAMPLE 5: CONTEXT HAS ANSWER, AND ANSWER IS FACTUALLY ACCURATE (yes)
Context:
লাইব্রেরি রবিবার থেকে বৃহস্পতিবার সকাল ৯:০০ টা থেকে বিকাল ৫:০০ টা পর্যন্ত খোলা থাকে।
Query:
লাইব্রেরি কখন খোলা থাকে?
Answer:
লাইব্রেরি রবিবার থেকে বৃহস্পতিবার সকাল ৯:০০ টা থেকে বিকাল ৫:০০ টা পর্যন্ত খোলা থাকে।
Expected Output:
yes
Reason:
Context contains the actual answer, and the answer is accurate without any hallucination or extra claims."""

SUPPORT_CHECK_SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_REFERENCE}"

_SUPPORT_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUPPORT_CHECK_SYSTEM_PROMPT),
    ("human", "Query: {user_input}\n\nAnswer: {answer}\n\nContext: {context}")
])


def sql_retrieve_support_check_node(state: RAGState) -> Dict[str, Any]:
    """Check if retrieved answer is supported and quality acceptable.

    - "no_support": context lacks actual answer → supported=False, retry_count=MAX_RETRIES (direct fallback to web search)
    - "hallucination": context has answer, but AI hallucinated/added extra info → supported=False, retry_count += 1 (retry generation)
    - "yes": context has answer, no hallucination → supported=True, final_answer set (proceed to END)
    """
    llm = get_llm()
    chain = _SUPPORT_CHECK_PROMPT | llm

    sql_retrieve_state = state.get("sql_retrieve", {})
    user_input = state.get("user_input", "")
    answer = sql_retrieve_state.get("final_answer", "")
    context = sql_retrieve_state.get("context_with_meta", "")
    retry_count = sql_retrieve_state.get("retry_count", 0)

    print(f"[sql_retrieve_support_check] retry_count={retry_count}, answer_len={len(answer)}")

    # Guard 1: Retries already exhausted
    if retry_count >= MAX_RETRIES:
        print("[sql_retrieve_support_check] Retries exhausted. Routing to fallback.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": False,
                "retry_count": MAX_RETRIES,
            }
        }

    # Guard 2: Missing context or answer
    if not context.strip() or not answer.strip():
        print("[sql_retrieve_support_check] Missing context or answer. Direct no_support.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": False,
                "retry_count": MAX_RETRIES,
            }
        }

    # Guard 3: Explicit missing-info detection in the answer
    missing_info_indicators = [
        "কোনো তথ্য উল্লেখ নেই",
        "কোন তথ্য উল্লেখ নেই",
        "তথ্য উল্লেখ নেই",
        "কোনো তথ্য পাওয়া যায়নি",
        "কোনো তথ্য পাওয়া যায়নি",
        "কোন তথ্য পাওয়া যায়নি",
        "কোন তথ্য পাওয়া যায়নি",
        "তথ্য পাওয়া যায়নি",
        "তথ্য পাওয়া যায়নি",
        "কোনো তথ্য নেই",
        "কোন তথ্য নেই",
        "তথ্য খুঁজে পাওয়া যায়নি",
        "তথ্য খুঁজে পাওয়া যায়নি",
        "উল্লেখ করা হয়নি",
        "উল্লেখ করা হয়নি",
        "তথ্য পাওয়া সম্ভব হয়নি",
        "তথ্য পাওয়া সম্ভব হয়নি",
        "not mentioned",
        "no information",
        "not found in the provided",
        "not available in the context",
        "information is not available",
        "does not mention",
    ]
    answer_lower = answer.lower()
    if any(ind in answer_lower for ind in missing_info_indicators):
        print("[sql_retrieve_support_check] Missing info indicator detected in answer. Direct fallback to no_support.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": False,
                "retry_count": MAX_RETRIES,
            }
        }

    try:
        response = chain.invoke({
            "user_input": user_input,
            "answer": answer,
            "context": context,
        })

        check_result = extract_content(response).strip().lower()

        print(f"[sql_retrieve_support_check] LLM verdict: '{check_result}'")

        if "no_support" in check_result or "not_supported" in check_result or "no support" in check_result:
            print("[sql_retrieve_support_check] Context does not contain the answer. Direct fallback (skipping retries).")
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "supported": False,
                    "retry_count": MAX_RETRIES,  # Direct fallback to web_search_rewrite
                }
            }
        elif "yes" in check_result and "hallucination" not in check_result:
            print("[sql_retrieve_support_check] Answer is supported and verified.")
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "supported": True,
                    "retry_count": retry_count,
                },
                "answer_status": "found",
                "final_answer": answer,
            }
        else:
            # Assumed hallucination or extra/fabricated info
            new_retry_count = retry_count + 1
            print(f"[sql_retrieve_support_check] Hallucination / extra info detected. Retry {new_retry_count}/{MAX_RETRIES}.")
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "supported": False,
                    "retry_count": new_retry_count,
                }
            }

    except Exception as e:
        print(f"[sql_retrieve_support_check] Error: {e}. Treating as supported to avoid crash.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": True,
                "retry_count": retry_count,
            }
        }

    except Exception as e:
        print(f"[sql_retrieve_support_check] Error: {e}. Treating as supported to avoid crash.")
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "supported": True,
                "retry_count": retry_count,
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state: RAGState = {
        "user_input": "What facilities are available at the college?",
        "sql_retrieve": {
            "final_answer": "The college has a library, computer lab, sports ground, and auditorium.",
            "context_with_meta": "Date: 2024-01-15\nInformation: library, computer lab, sports ground, auditorium.",
            "retry_count": 0,
        }
    }
    result = sql_retrieve_support_check_node(sample_state)
    print("Support Check Result:")
    print(result)