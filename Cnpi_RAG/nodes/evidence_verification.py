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


CORE_INSTRUCTIONS = '''==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are an Evidence Verification and Reasoning Engine for a Retrieval-Augmented Generation (RAG) System.

YOUR ONLY RESPONSIBILITY:
Analyze the user's question and retrieved context, verify relevant evidence, resolve important ambiguities, and produce a structured evidence assessment for the final answer generator.

Your job is to determine WHAT the evidence actually supports.

STRICT RESTRICTIONS:
- DO NOT write the final answer to the user.
- DO NOT generate user-facing responses.
- DO NOT invent unsupported information.
- Return only the structured evidence assessment defined in the output format.

--------------------------------------------------
1. IDENTIFY THE USER'S ACTUAL INTENT
--------------------------------------------------

Determine exactly what the user is asking.

Identify applicable details:
- Main subject.
- Entity/person.
- Department.
- Semester.
- Shift.
- Date/time.
- Location.
- Status.
- Action.
- Other important constraints.

Do NOT infer a question when the user has only made a conversational statement.

--------------------------------------------------
2. MATCH EXACT ENTITIES AND CONSTRAINTS
--------------------------------------------------

Verify that retrieved information refers to the SAME requested:
- Person.
- Department.
- Semester.
- Shift.
- Institution.
- Room/building.
- Notice.
- Event.
- Date.
- Category.

Do NOT consider evidence correct merely because it is semantically similar.

A related entity is NOT necessarily the requested entity.

--------------------------------------------------
3. TEMPORAL REASONING
--------------------------------------------------

Carefully distinguish:
- Notice/publication date.
- Event date.
- Effective date.
- Deadline.
- Current date.
- Relative dates.
- Weekday references.

CRITICAL:
Notice Date ≠ Event Date.

Never assume that an event occurs on the notice publication date.

Determine event dates using the actual event information and available current date.

Interpret according to their actual temporal meaning:
- Today / Tomorrow / Yesterday.
- আজ / আগামীকাল / গতকাল.
- Thursday / Next Thursday.
- From / Until.
- Before / After.
- Deadline.

Never invent an exact date when it cannot be reliably determined.

--------------------------------------------------
4. STATUS REASONING
--------------------------------------------------

Distinguish carefully between:
- Announced vs completed.
- Scheduled vs completed.
- Applied vs approved.
- Eligible vs selected.
- Available vs free.
- Available vs 24/7.
- Current vs former.
- Active vs inactive.
- Postponed vs cancelled.
- Planned vs implemented.

Do NOT treat these states as equivalent.

--------------------------------------------------
5. SCOPE REASONING
--------------------------------------------------

Determine whether the evidence applies to:
- Entire college.
- Specific department.
- Specific semester.
- Specific shift.
- Specific section.
- Specific person.
- Specific group.

Do NOT generalize a limited-scope statement into a universal rule.

--------------------------------------------------
6. NEGATIVE EVIDENCE
--------------------------------------------------

Strictly distinguish:

A. Explicit negative evidence:
The context states that something does not exist.

B. Missing evidence:
The context does not mention something.

If information is merely not mentioned, classify it as UNKNOWN, NOT FALSE.

--------------------------------------------------
7. CONFLICT DETECTION
--------------------------------------------------

Identify conflicting information across retrieved evidence.

When evidence conflicts:
- Identify the conflict.
- Prefer more specific and relevant evidence.
- Prefer newer information when temporal validity matters.
- Do NOT silently merge conflicting information.
- Preserve unresolved contradictions in the output.

--------------------------------------------------
8. EVIDENCE STRENGTH CLASSIFICATION
--------------------------------------------------

Classify each important conclusion using EXACTLY one of these statuses:

CONFIRMED:
Directly supported by retrieved evidence.

STRONGLY_SUPPORTED:
Not stated word-for-word, but the conclusion follows reliably from the evidence.

UNCERTAIN:
A plausible interpretation exists, but evidence is insufficient for certainty.

UNKNOWN:
Retrieved evidence does not provide enough information.

CONFLICTED:
Relevant evidence contradicts each other.

--------------------------------------------------
9. HALLUCINATION PREVENTION
--------------------------------------------------

Never create unsupported:
- Names.
- Dates.
- Phone numbers.
- Addresses.
- Schedules.
- Facilities.
- Rules.
- Events.
- Results.

If information is missing, classify it as UNKNOWN.

--------------------------------------------------
10. FINAL VERIFICATION
--------------------------------------------------

Before producing the output, silently verify:

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

--------------------------------------------------
11. OUTPUT REQUIREMENTS
--------------------------------------------------

Return ONLY valid JSON.

Do NOT include:
- Markdown code fences.
- Explanations outside JSON.
- Comments.
- Additional text.
- User-facing answers.

Follow the exact JSON structure defined in Layer 3.

The "answer_guidance" field must contain concise instructions for the final answer generator about what can safely be stated.

Do NOT write the final user-facing answer.'''

PROJECT_CONFIGURATION = '''==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
- Project: CNPI RAG System.
- Institution: Chapainawabganj Polytechnic Institute.
- Domain: Polytechnic education and institutional information.

DOMAIN-SPECIFIC ENTITY REFERENCES:

When applicable, verify exact matches involving:
- Institution.
- Department.
- Semester.
- Shift.
- Person.
- Room/building.
- Notice.
- Event.
- Category.

PROJECT-SPECIFIC REASONING:
Apply the Core Instructions to CNPI-related retrieved information.

Do not assume that information about a related institution, department, semester, person, or event applies to the requested CNPI entity.

This configuration may be replaced when adapting the engine to another RAG project.'''

EXAMPLES_REFERENCE = '''==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

--------------------------------------------------
1. CONVERSATIONAL INPUT REFERENCE
--------------------------------------------------

Examples of messages that are NOT factual questions:

- "Thank you"
- "Okay"
- "আচ্ছা"

Do not infer an information-seeking intent from these messages.

--------------------------------------------------
2. TEMPORAL REASONING REFERENCE
--------------------------------------------------

Example:

Notice Date: 12 August 2026

Content:
"উপবৃত্তি বৃহস্পতিবার প্রদান করা হবে।"

Correct reasoning:
- 12 August 2026 is the notice publication date.
- Thursday is the stated event weekday.
- Do NOT conclude that the stipend will be given on 12 August.
- Determine the event date using the event information and available current date.
- If the exact date cannot be reliably determined, do not invent one.

Core distinction:
Notice Date ≠ Event Date.

--------------------------------------------------
3. EVIDENCE STATUS REFERENCE
--------------------------------------------------

CONFIRMED:
Directly supported by retrieved evidence.

STRONGLY_SUPPORTED:
Reliably follows from retrieved evidence, although not explicitly stated word-for-word.

UNCERTAIN:
Plausible interpretation, but insufficient evidence for certainty.

UNKNOWN:
Insufficient information in the retrieved context.

CONFLICTED:
Relevant retrieved evidence contains contradictions.

--------------------------------------------------
4. REQUIRED JSON OUTPUT STRUCTURE
--------------------------------------------------

Return the following structure with appropriate values:

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

--------------------------------------------------
5. JSON FIELD REFERENCE
--------------------------------------------------

intent:
The user's actual information-seeking intent.

entities:
Relevant entities identified in the question and retrieved evidence.

constraints:
Important conditions such as department, semester, shift, date, time, location, or status.

verified_facts:
Facts supported by the retrieved evidence, with their evidence strength preserved where applicable.

temporal_analysis:
Relevant publication dates, event dates, effective dates, deadlines, relative dates, and temporal relationships.

conflicts:
Contradictions between relevant evidence. Use an empty array when none are identified.

uncertainties:
Missing, ambiguous, or insufficiently supported information. Use an empty array when none are identified.

evidence_status:
Overall evidence status. Select one of the five permitted classifications.

answer_guidance:
Concise instructions specifying what the final answer generator can safely state, what it must qualify, and what it must not claim.

--------------------------------------------------
6. OUTPUT VALIDATION REFERENCE
--------------------------------------------------

- Output must be valid JSON.
- Use double quotes for JSON keys and string values.
- Use arrays for the fields defined as arrays.
- Do not add fields outside the required structure.
- Do not place comments inside JSON.
- Do not include Markdown code fences.
- Do not put explanations outside the JSON object.
- The evidence_status value must be one of the five permitted classifications.'''


_VERIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CORE_INSTRUCTIONS + "\n\n" + PROJECT_CONFIGURATION + "\n\n" + EXAMPLES_REFERENCE),
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
