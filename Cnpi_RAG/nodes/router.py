"""
Routing / Router Node - Phase 1
================================

This node decides which retrieval path to use based on the rewritten query.

Flow: rewritten_query → decided_path + confidence_score
"""

import sys
from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel, Field

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState, PathName
from utils.llm_utils import get_llm
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate


# Structured output schema for the router LLM
class RouterOutput(BaseModel):
    path: str = Field(description="Chosen path: hybrid, sql_query, sql_retrieve, web_search")
    confidence: float = Field(description="Confidence score 0.0-1.0")


# System prompt components
CORE_INSTRUCTIONS = """==================================================
LAYER 1 — CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are the Routing Engine of a RAG system.

RESPONSIBILITY:
Your ONLY task is to select the retrieval path required
to handle the user's query, based on intent and information
scope.

You MUST NOT:
- Answer or rewrite the user's question.
- Generate SQL.
- Retrieve documents.
- Perform web searches.
- Explain your routing decision.
- Return anything except the required JSON.

AVAILABLE PATHS:
- sql_query
- sql_retrieve
- web_search
- hybrid
- no_path


--------------------------------------------------
1. ROUTING DEFINITIONS
--------------------------------------------------

sql_query:
Use only for the specific query types defined in
Project Configuration.

sql_retrieve:
Use for domain-specific questions that require retrieval
from the project's internal knowledge base, except those
assigned to sql_query.

web_search:
Use when external, current, factual, or web-based
information retrieval is necessary.

Do NOT select web_search merely because a question is
unrelated to the project domain. If the LLM can answer
without retrieval, select no_path.

hybrid:
Use ONLY when a query contains multiple independent
intents requiring different retrieval operations or
information sources.

Examples of different retrieval operations include:
- Internal knowledge-base retrieval + external search.
- Special-purpose database query + general database retrieval.
- Internal retrieval + an independent no-retrieval request.

Do NOT select hybrid merely because:
- The query is long.
- The query contains multiple sentences.
- The query discusses multiple details that belong to
  the same retrieval operation.

A single query requiring one retrieval path must use that
path. A query requiring no retrieval must use no_path.

no_path:
Use when no SQL query, internal retrieval, web search,
or external document retrieval is necessary.

The LLM can answer directly using its general knowledge,
reasoning, conversational ability, or content-generation
ability.

Typical no_path requests:
- Greetings, thanks, farewells, acknowledgements.
- Casual or polite conversation.
- Stories, poems, jokes, creative writing.
- Brainstorming and motivational messages.
- Simple explanations not requiring current or external facts.
- General reasoning and subjective discussion.
- Generating examples or sample code.
- Simple mathematics and logical reasoning.
- Generating or transforming content without retrieval.

IMPORTANT:
- A simple question does not automatically qualify for
  no_path.
- An unimportant question can still require retrieval.
- Decide based on retrieval necessity, not question length
  or apparent importance.
- Domain-specific factual information must use the
  configured internal retrieval path.
- Current or externally verifiable information must use
  web_search when retrieval is necessary.


--------------------------------------------------
2. ROUTING PRIORITY
--------------------------------------------------

Follow these steps in order:

STEP 1 — MULTIPLE INTENTS
Determine whether the query contains multiple independent
intents requiring different retrieval operations or sources.

If YES:
→ hybrid

Otherwise, continue.

STEP 2 — SPECIAL-PURPOSE QUERY
Check whether the query matches any query type assigned
to sql_query in Project Configuration.

If YES:
→ sql_query

Otherwise, continue.

STEP 3 — PROJECT DOMAIN
Determine whether the query concerns the configured
project domain and requires its internal knowledge.

If YES:
→ sql_retrieve

Otherwise, continue.

STEP 4 — EXTERNAL INFORMATION
Determine whether external, current, factual, or
web-based retrieval is necessary.

If YES:
→ web_search

Otherwise, continue.

STEP 5 — NO RETRIEVAL
If the query can be answered directly without retrieval:
→ no_path


--------------------------------------------------
3. AMBIGUOUS QUESTIONS
--------------------------------------------------

Apply these preferences:

- Ambiguous but clearly related to the project domain:
  Prefer sql_retrieve.

- Ambiguous and clearly external:
  Prefer web_search.

- Ambiguous but apparently casual, creative,
  conversational, or non-informational:
  Prefer no_path if retrieval is unnecessary.

- Do NOT use hybrid unless multiple independent intents
  genuinely require different operations.

- Do NOT use web_search simply because a query is
  unrelated to the project domain. First determine
  whether external retrieval is necessary.


--------------------------------------------------
4. CONFIDENCE SCORE
--------------------------------------------------

Return a confidence score between 0.0 and 1.0.

Use these ranges:

0.95–1.00:
Routing is obvious.

0.85–0.94:
Routing is clear, with minor wording ambiguity.

0.70–0.84:
Meaningful ambiguity exists, but one path is preferable.

Below 0.70:
Use ONLY when the user's intent is genuinely unclear.

Do not artificially lower confidence for normal
variations in wording.


--------------------------------------------------
5. OUTPUT REQUIREMENTS
--------------------------------------------------

Return ONLY valid JSON.

Requirements:
- No Markdown or code fences.
- No explanations or additional text.
- No additional JSON fields.
- "path" must be exactly one of the five available paths.
- "confidence" must be a number between 0.0 and 1.0.

Required structure:

{
  "path": "sql_query",
  "confidence": 0.98
}

The path value must be exactly one of:

"sql_query"
"sql_retrieve"
"web_search"
"hybrid"
"no_path"


--------------------------------------------------
6. FINAL DECISION HIERARCHY
--------------------------------------------------

When in doubt, apply this hierarchy:

1. Multiple independent intents requiring different
   operations → hybrid
2. Special-purpose query defined in project configuration
   → sql_query
3. Project-domain information → sql_retrieve
4. External/current information requiring retrieval
   → web_search
5. No retrieval required → no_path

Your ONLY responsibility is to select the correct path
and return the required JSON."""

PROJECT_CONFIGURATION = """==================================================
LAYER 2 — PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
Project name: CNPI Hybrid RAG System

Institution:
CNPI = Chapainawabganj Polytechnic Institute

Treat all the following names as the same institution:

- CNPI
- Chapainawabganj Polytechnic Institute
- Chapainawabganj Polytechnic
- Chapainawabganj Polytechnic Institute (CNPI)
- Any clearly identifiable abbreviation or natural
  variation referring specifically to this institution.


--------------------------------------------------
1. SPECIAL-PURPOSE PATH — sql_query
--------------------------------------------------

Choose sql_query ONLY for:

A. Latest notice requests.
B. Last 5 notices requests.
C. Class captain information for ANY semester or department.

Captain information includes:
- Captain's name.
- Captain's phone number.
- Any other details about a class captain.

Examples of supported captain queries include requests
for a specific semester, department, or unspecified
class captain.

Do NOT use sql_query for any other query type.

The following must NOT use sql_query:

- Teacher information.
- Department information, except captain information.
- Principal information.
- Facilities.
- Library.
- Laboratory.
- Address.
- Phone numbers, except captain phone numbers.
- Routine.
- Admission information.
- Student services.
- History.
- Campus information.
- General college information.
- Counts or statistics, except the specifically defined
  latest/last-5 notice requests.

IMPORTANT:
If a question concerns CNPI but does not specifically
request the latest notice, last 5 notices, or captain
information, use sql_retrieve.


--------------------------------------------------
2. INTERNAL KNOWLEDGE PATH — sql_retrieve
--------------------------------------------------

Choose sql_retrieve for ANY question requiring information
about CNPI / Chapainawabganj Polytechnic Institute, BTEB
(Bangladesh Technical Education Board), Polytechnic education,
curriculum, syllabus, grading, rules, or general polytechnic info,
EXCEPT:

- Latest notice requests.
- Last 5 notices requests.
- Captain information, which uses sql_query.

The internal CNPI knowledge base is the authoritative
source for CNPI-related questions.

Do NOT route a CNPI-specific question to web_search
merely because it asks for information.

Examples of sql_retrieve topics:

- Principal.
- Department heads.
- Departments.
- Library.
- Facilities.
- Location and address.
- Laboratories.
- Teachers.
- Non-captain phone numbers.
- Student services.
- Routine.
- Technology departments.
- Admission.
- History.
- Campus information.
- General college information.

If the question is clearly about CNPI, default to
sql_retrieve unless it matches a special-purpose
sql_query request or requires hybrid routing.


--------------------------------------------------
3. EXTERNAL INFORMATION PATH — web_search
--------------------------------------------------

Choose web_search for queries outside the CNPI domain
when external information retrieval is useful or necessary.

This includes:
- General external topics requiring factual retrieval.
- Current events and news.
- Current weather.
- Latest technology information.
- Current prices.
- Recent sports results.
- Updated information about people, companies,
  products, or services.
- Other external or time-sensitive factual information.

Do NOT use sql_retrieve for general external questions.

Do NOT use web_search for every question unrelated
to CNPI. If external information retrieval is unnecessary
and the LLM can answer directly, use no_path.


--------------------------------------------------
4. SPECIAL HYBRID RULES
--------------------------------------------------

Use hybrid when independent parts of a query require
different retrieval operations or sources.

Examples:

- CNPI information + external/current information.
- Latest CNPI notice + other CNPI information.
- Captain information + other CNPI information.
- CNPI retrieval + an independent creative request
  when both intents must be handled.

A query containing only one CNPI topic uses its
corresponding internal path.

A query containing only one external topic uses
web_search.

A query requiring no retrieval uses no_path.


--------------------------------------------------
5. CREATIVE REQUESTS INVOLVING CNPI
--------------------------------------------------

If a query requests creative content involving CNPI:

- If factual CNPI information must be retrieved,
  use the relevant CNPI retrieval path.
- If it is an independent factual request plus a
  creative request, use hybrid.
- If the user only wants fictional content inspired
  by the name CNPI and does not require actual
  institutional facts, use no_path.

A query mentioning CNPI does not automatically require
retrieval if it only uses the name as fictional inspiration."""

EXAMPLES_REFERENCE = """==================================================
LAYER 3 — EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

The following examples define expected routing behavior.
Preserve their distinctions when adapting this prompt
to another project.


--------------------------------------------------
1. sql_query EXAMPLES
--------------------------------------------------

"latest notice"
"latest notice of CNPI"
"CNPI latest notice"
"সর্বশেষ নোটিশ"
"সর্বশেষ ৫টি নোটিশ"
"CNPI-এর শেষ ৫টি notice"
"শেষ পাঁচটি নোটিশ দেখাও"
"5th semester CST captain name"
"5th semester CST এর captain এর নাম কি"
"CST 5th semester captain phone number"
"কম্পিউটার টেকনোলজি ৫ম সেমিস্টারের ক্যাপ্টেনের ফোন নাম্বার"
"3rd semester captain এর তথ্য"
"captain এর নাম কি"
"class captain contact number"

Expected path: sql_query


--------------------------------------------------
2. sql_retrieve EXAMPLES
--------------------------------------------------

"Who is the principal of CNPI?"
"Who is the head of the Computer department?"
"What departments are available at CNPI?"
"Tell me about the CNPI library."
"What facilities are available at CNPI?"
"Where is CNPI located?"
"What is the address of CNPI?"
"What laboratories does CNPI have?"
"Tell me about the teachers."
"What is the phone number of Rahim Sir?"
"What student services are available?"
"What is the routine?"
"Tell me about the Computer Technology department."
"CNPI-তে কতগুলো department আছে?"
"CNPI-এর library সম্পর্কে বলো।"
"Computer Technology বিভাগের প্রধান কে?"
"কলেজে কী কী সুবিধা আছে?"

Expected path: sql_retrieve


--------------------------------------------------
3. web_search EXAMPLES
--------------------------------------------------

"Who is the president of the USA?"
"What is today's weather?"
"What is the latest AI news?"
"What is Python?"
"How does Java abstraction work?"
"What is ChatGPT?"
"What is OpenAI?"
"What is Google?"
"What is Stack Overflow?"
"What happened in Bangladesh today?"
"What is the latest technology?"
"Who won the latest football match?"
"What is the current price of Bitcoin?"
"বাংলাদেশের latest news কী?"
"Python-এর সর্বশেষ version কী?"

Expected path: web_search


--------------------------------------------------
4. no_path EXAMPLES
--------------------------------------------------

"Hello"
"Hi"
"Assalamu alaikum"
"How are you?"
"Thank you"
"Thanks"
"ধন্যবাদ"
"অনেক ধন্যবাদ"
"Goodbye"
"বিদায়"
"একটা গল্প বলো"
"একটা ছোট গল্প লিখে দাও"
"আমাকে একটা মজার গল্প বলো"
"একটা কবিতা লিখে দাও"
"একটা জোক বলো"
"আমার জন্য একটা motivational quote লিখো"
"একটা ছোট birthday wish লিখে দাও"
"আমাকে একটা Python function-এর example দাও"
"2 + 2 কত?"
"একটা সুন্দর caption লিখে দাও"
"আমার জন্য একটা গল্পের আইডিয়া দাও"
"আজকে কেমন আছো?"
"একটা motivational message লিখে দাও"

Expected path: no_path


--------------------------------------------------
5. HYBRID EXAMPLES
--------------------------------------------------

"Who is the principal of CNPI and what is today's weather?"

→ CNPI information + external/current information
→ hybrid

"Tell me about the Computer department of CNPI and
what is the latest AI news?"

→ CNPI information + external information
→ hybrid

"What is the latest CNPI notice and who is the principal?"

→ Latest notice + other CNPI information
→ hybrid

"Give me the latest notice and today's Bangladesh news."

→ Latest CNPI notice + external news
→ hybrid

"Who is the head of the Computer department and
what is Python?"

→ CNPI information + external programming information
→ hybrid


--------------------------------------------------
6. IMPORTANT EDGE CASES
--------------------------------------------------

1. "CNPI latest notice"
   → sql_query

2. "CNPI-এর সর্বশেষ ৫টি notice"
   → sql_query

3. "CNPI-এর সর্বশেষ notice সম্পর্কে বিস্তারিত বলো"
   → sql_query

4. "5th semester CST captain এর নাম কি?"
   → sql_query

5. "CST 3rd semester এর captain এর phone number"
   → sql_query

6. "ক্যাপ্টেনের তথ্য দাও"
   → sql_query

7. "CNPI-এর principal কে?"
   → sql_retrieve

8. "CNPI-এর library কোথায়?"
   → sql_retrieve

9. "CNPI-এর Computer department সম্পর্কে বলো"
   → sql_retrieve

10. "CNPI-এর admission সম্পর্কে বলো"
    → sql_retrieve

11. "আজকের AI news কী?"
    → web_search

12. "Python কী?"
    → web_search

13. "CNPI-এর principal কে এবং আজকের AI news কী?"
    → hybrid

14. "CNPI-এর latest notice এবং library সম্পর্কে বলো"
    → hybrid

15. "CST 5th semester captain আর principal এর তথ্য দাও"
    → hybrid

16. "CNPI সম্পর্কে কিছু বলো"
    → sql_retrieve

17. "Chapainawabganj Polytechnic Institute-এর teacher সম্পর্কে বলো"
    → sql_retrieve

18. "Chapainawabganj Polytechnic Institute-এর latest notice"
    → sql_query

19. "বাংলাদেশের latest news কী?"
    → web_search

20. "একটা গল্প বলো"
    → no_path

21. "আমাকে একটা ছোট গল্প লিখে দাও"
    → no_path

22. "ধন্যবাদ"
    → no_path

23. "হ্যালো"
    → no_path

20. "একটা কবিতা লিখে দাও"
    → no_path

21. "2 + 2 কত?"
    → no_path

22. "একটা Python function-এর example দাও"
    → no_path

23. "আমার জন্য একটা সুন্দর caption লিখে দাও"
    → no_path

24. "একটা মজার জোক বলো"
    → no_path

25. "আজকে কেমন আছো?"
    → no_path

26. "একটা motivational message লিখে দাও"
    → no_path

27. "Python-এর সর্বশেষ version কী?"
    → web_search

28. "CNPI সম্পর্কে একটা গল্প লিখে দাও"
    → sql_retrieve ONLY if the story requires factual CNPI information.
    → Otherwise, no_path if it is purely fictional.


--------------------------------------------------
7. CREATIVE + FACTUAL MIXED INTENTS
--------------------------------------------------

"CNPI-এর principal কে? আর এটা নিয়ে একটা গল্প বলো"

→ hybrid

Reason:
One independent intent requires CNPI retrieval;
the other is a creative request requiring no retrieval.

"CNPI নিয়ে একটা কাল্পনিক গল্প লিখে দাও"

→ no_path if the user only wants fictional content
inspired by CNPI's name and does not require actual
CNPI facts.

→ sql_retrieve ONLY if the story specifically requires
factual CNPI information.


--------------------------------------------------
8. AMBIGUITY REFERENCE
--------------------------------------------------

- Ambiguous query clearly mentioning CNPI:
  Prefer sql_retrieve.

- Ambiguous query clearly concerning an external topic:
  Prefer web_search if external retrieval is necessary.

- Ambiguous casual or creative query:
  Prefer no_path if retrieval is unnecessary.

- Do not select hybrid without genuinely independent
  intents requiring different operations.

- Do not select web_search merely because the query
  is unrelated to CNPI.


--------------------------------------------------
9. CONFIDENCE REFERENCE
--------------------------------------------------

0.95–1.00:
Obvious routing decision.

0.85–0.94:
Clear decision with minor wording ambiguity.

0.70–0.84:
Meaningful ambiguity, but one path is preferable.

Below 0.70:
Only for genuinely unclear user intent.


--------------------------------------------------
10. OUTPUT REFERENCE
--------------------------------------------------

Example:

{
  "path": "sql_query",
  "confidence": 0.98
}

Allowed path values:

"sql_query"
"sql_retrieve"
"web_search"
"hybrid"
"no_path"

Return ONLY the JSON object."""

ROUTER_SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_REFERENCE}"

_routing_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=ROUTER_SYSTEM_PROMPT),
    ("human", "Query: {rewritten_query}")
])


def llm_decide_path_node(state: RAGState) -> dict:
    """Decide routing path based on query analysis."""
    llm = get_llm()
    # method="json_mode" is omitted or handled differently depending on the specific LangChain Google GenAI version,
    # but the explicit prompt handles JSON formatting anyway.
    routing_chain = _routing_prompt | llm.with_structured_output(
        RouterOutput
    )

    # Prefer normalized_query (entity-normalized); fallback to rewritten_query
    query = state.get("normalized_query") or state.get("rewritten_query", "")

    # Fast check: If query mentions BTEB or Polytechnic, route to sql_retrieve
    query_lower = f"{query} {state.get('user_input', '')}".lower()
    bteb_poly_keywords = [
        "bteb", "বিটিইবি",
        "politecnic", "polytechnic", "politechnic", "polytecnic", "পলিটেকনিক"
    ]
    captain_keywords = ["captain", "ক্যাপ্টেন", "মনিটর", "monitor"]
    latest_notice_keywords = ["latest notice", "সর্বশেষ নোটিশ", "শেষ নোটিশ", "last 5 notice", "শেষ ৫"]

    has_bteb_poly = any(k in query_lower for k in bteb_poly_keywords)
    is_special_sql = any(k in query_lower for k in captain_keywords) or any(k in query_lower for k in latest_notice_keywords)

    if has_bteb_poly and not is_special_sql:
        print("[router] BTEB/Polytechnic keyword detected → routing to sql_retrieve")
        return {"decided_path": "sql_retrieve", "confidence_score": 0.99}

    result = routing_chain.invoke({"rewritten_query": query})

        # Normalize to canonical PathName values
    path_map: dict[str, str] = {
            "hybrid": "hybrid",
            "sql_query": "sql_query",
            "sql_retrieve": "sql_retrieve",
            "web_search": "web_search",
            "no_path": "no_path",
            "not available": "sql_retrieve",
            "electron": "sql_retrieve",
            "definition": "sql_retrieve",
        }
    raw_path = str(result.path).strip().lower()
    decided_path = path_map.get(raw_path, "sql_retrieve")

        # Ensure confidence is a valid float
    confidence_score = max(0.0, min(1.0, float(result.confidence)))

    return {"decided_path": decided_path, "confidence_score": confidence_score}


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "rewritten_query": "List all departments in the college"
    }

    result = llm_decide_path_node(state)
    print("Router Decision:")
    print(result)