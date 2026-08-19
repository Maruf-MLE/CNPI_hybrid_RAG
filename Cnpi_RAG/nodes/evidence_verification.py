"""
Evidence Verification and Reasoning Node
==========================================

This node sits between context retrieval and final answer generation.
Its job is to analyze the user's query and retrieved context, verify evidence,
resolve temporal ambiguities, and produce a structured evidence assessment
for the final answer generator.

Flow: user_input + context → verified evidence JSON → passed to response node

This node DOES NOT generate the final answer. It only verifies and structures
the evidence that the answer generator will use.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


_VERIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are the Evidence Verification and Reasoning Engine of the CNPI RAG System.

Your ONLY responsibility is to analyze the user's question and the retrieved context, verify the relevant evidence, resolve important ambiguities, and produce a structured evidence assessment for the final answer generator.

DO NOT write the final answer to the user.

Your job is to determine WHAT the evidence actually supports.

==================================================
1. IDENTIFY THE USER'S ACTUAL INTENT
==================================================

Determine exactly what the user is asking.

Identify, when applicable:

- main subject
- entity/person
- department
- semester
- shift
- date/time
- location
- status
- action
- other important constraints

Do not infer a question when the user has only made a conversational statement.

For example:

"Thank you"
"Okay"
"আচ্ছা"

are not factual questions.

==================================================
2. MATCH THE EXACT ENTITY AND CONSTRAINTS
==================================================

Verify that the retrieved information refers to the SAME:

- person
- department
- semester
- shift
- institution
- room/building
- notice
- event
- date
- category

Do NOT consider a result correct merely because it is semantically similar.

A related entity is NOT the requested entity.

==================================================
3. TEMPORAL REASONING
==================================================

Carefully distinguish:

- notice/publication date
- event date
- effective date
- deadline
- current date
- relative dates
- weekday references

IMPORTANT:

Notice Date ≠ Event Date.

For example:

Notice Date: 12 August 2026
Content: "উপবৃত্তি বৃহস্পতিবার প্রদান করা হবে।"

Do NOT conclude that the stipend will be given on 12 August.

Determine the event date from the event information and the available current date.

Interpret:

- today
- tomorrow
- yesterday
- আজ/আগামীকাল/গতকাল
- Thursday
- next Thursday
- from
- until
- before
- after
- deadline

according to their actual temporal meaning.

Never invent an exact date when it cannot be reliably determined.

==================================================
4. STATUS REASONING
==================================================

Distinguish carefully between:

- announced vs completed
- scheduled vs completed
- applied vs approved
- eligible vs selected
- available vs free
- available vs 24/7
- current vs former
- active vs inactive
- postponed vs cancelled
- planned vs implemented

Do not treat these as equivalent.

==================================================
5. SCOPE REASONING
==================================================

Determine whether the evidence applies to:

- entire college
- specific department
- specific semester
- specific shift
- specific section
- specific person
- specific group

Do not generalize a limited-scope statement into a universal rule.

==================================================
6. NEGATIVE EVIDENCE
==================================================

Strictly distinguish:

"The context says something does not exist."

from:

"The context does not mention it."

If something is merely not mentioned, classify it as UNKNOWN rather than FALSE.

==================================================
7. CONFLICT DETECTION
==================================================

Look for conflicting information.

If multiple pieces of evidence conflict:

- identify the conflict
- prefer the more specific and relevant evidence
- prefer newer information when temporal validity matters
- do not silently merge conflicting information

==================================================
8. EVIDENCE STRENGTH
==================================================

Classify each important conclusion as one of:

CONFIRMED
- Directly supported by the retrieved evidence.

STRONGLY_SUPPORTED
- Not stated word-for-word, but the conclusion follows reliably from the evidence.

UNCERTAIN
- A plausible interpretation exists, but the evidence is insufficient for certainty.

UNKNOWN
- The retrieved evidence does not provide enough information.

CONFLICTED
- Relevant evidence contradicts each other.

==================================================
9. DO NOT HALLUCINATE
==================================================

Never create:

- names
- dates
- phone numbers
- addresses
- schedules
- facilities
- rules
- events
- results

that are not supported by the evidence.

If information is missing, mark it UNKNOWN.

==================================================
10. FINAL VERIFICATION
==================================================

Before producing your output, silently verify:

1. Did I identify the exact user intent?
2. Did I match the exact entity?
3. Did I check all important constraints?
4. Did I distinguish notice date from event date?
5. Did I check temporal relationships?
6. Did I check scope?
7. Did I check status?
8. Did I detect conflicts?
9. Did I distinguish "not mentioned" from "does not exist"?
10. Did I avoid unsupported assumptions?

==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

{{
  "intent": "...",
  "entities": [],
  "constraints": [],
  "verified_facts": [],
  "temporal_analysis": [],
  "conflicts": [],
  "uncertainties": [],
  "evidence_status": "CONFIRMED | STRONGLY_SUPPORTED | UNCERTAIN | UNKNOWN | CONFLICTED",
  "answer_guidance": "..."
}}

The "answer_guidance" field should contain concise instructions for the final answer generator about what can safely be stated.

Do not write the final user-facing answer."""),
    ("human", """User Query: {user_query}

Current Date & Time: {current_datetime}

Retrieved Context:
{context}

Analyze the above and return ONLY the verification JSON.""")
])


def evidence_verification_node(state: RAGState) -> Dict[str, Any]:
    """Verify and structure evidence before final answer generation.
    
    This node analyzes the user query and retrieved context to produce
    a structured evidence assessment (JSON format) that will be passed
    to the final answer generator.
    
    Input: user_input + context from decided_path
    Output: verified_evidence field added to the appropriate path state
    """
    llm = get_llm()
    chain = _VERIFICATION_PROMPT | llm
    
    decided_path = state.get("decided_path", "sql_retrieve")
    user_input = state.get("user_input", "")
    normalized_query = state.get("normalized_query") or state.get("rewritten_query") or user_input
    
    # Get context based on the decided path
    context = ""
    path_state = {}
    
    if decided_path == "sql_query":
        sql_query_state = state.get("sql_query", {})
        context = sql_query_state.get("optimized_context") or sql_query_state.get("raw_context", "")
        path_state = sql_query_state
    elif decided_path == "sql_retrieve":
        sql_retrieve_state = state.get("sql_retrieve", {})
        context = sql_retrieve_state.get("context_with_meta", "")
        path_state = sql_retrieve_state
    elif decided_path == "web_search":
        web_search_state = state.get("web_search", {})
        context = web_search_state.get("context", "")
        path_state = web_search_state
    
    # If no context available, skip verification
    if not context or not context.strip():
        verification_result = {
            "intent": "Query analysis",
            "entities": [],
            "constraints": [],
            "verified_facts": [],
            "temporal_analysis": [],
            "conflicts": [],
            "uncertainties": ["No context available for verification"],
            "evidence_status": "UNKNOWN",
            "answer_guidance": "No evidence available to support an answer."
        }
        
        return {
            decided_path: {
                **path_state,
                "verified_evidence": json.dumps(verification_result, ensure_ascii=False)
            }
        }
    
    try:
        response = chain.invoke({
            "user_query": normalized_query,
            "context": context,
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        })
        
        verification_text = extract_content(response)
        if isinstance(verification_text, list):
            verification_text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block) 
                for block in verification_text
            )
        
        verification_text = verification_text.strip()
        
        # Extract JSON from the response (handle cases where LLM adds extra text)
        # Look for JSON object in the response
        if "{" in verification_text and "}" in verification_text:
            start_idx = verification_text.find("{")
            end_idx = verification_text.rfind("}") + 1
            json_str = verification_text[start_idx:end_idx]
            
            # Validate it's proper JSON
            try:
                verification_data = json.loads(json_str)
                verification_text = json.dumps(verification_data, ensure_ascii=False)
            except json.JSONDecodeError:
                # If parsing fails, wrap the text in a basic structure
                verification_text = json.dumps({
                    "intent": "Query analysis",
                    "entities": [],
                    "constraints": [],
                    "verified_facts": [verification_text],
                    "temporal_analysis": [],
                    "conflicts": [],
                    "uncertainties": [],
                    "evidence_status": "UNCERTAIN",
                    "answer_guidance": "Use the verified facts provided."
                }, ensure_ascii=False)
        
        # Store verified evidence in the appropriate path state
        return {
            decided_path: {
                **path_state,
                "verified_evidence": verification_text
            }
        }
        
    except Exception as e:
        error_msg = f"Evidence verification error: {str(e)}"
        print(f"[evidence_verification] {error_msg}")
        
        # On error, pass through with minimal verification
        fallback_verification = {
            "intent": "Query analysis",
            "entities": [],
            "constraints": [],
            "verified_facts": ["Verification process encountered an error"],
            "temporal_analysis": [],
            "conflicts": [],
            "uncertainties": ["Verification incomplete due to processing error"],
            "evidence_status": "UNCERTAIN",
            "answer_guidance": "Proceed with caution using available context."
        }
        
        return {
            decided_path: {
                **path_state,
                "verified_evidence": json.dumps(fallback_verification, ensure_ascii=False)
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    sample_state = {
        "user_input": "আজকে কি উপবৃত্তি দেওয়া হবে?",
        "decided_path": "sql_retrieve",
        "sql_retrieve": {
            "context_with_meta": """Notice Date: 12 August 2026
Title: উপবৃত্তি বিতরণ
Content: উপবৃত্তি বৃহস্পতিবার প্রদান করা হবে।
"""
        }
    }
    
    result = evidence_verification_node(sample_state)
    print("Evidence Verification Result:")
    print(json.dumps(json.loads(result["sql_retrieve"]["verified_evidence"]), indent=2, ensure_ascii=False))
