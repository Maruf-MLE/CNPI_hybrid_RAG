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
from langchain_core.prompts import ChatPromptTemplate


# Structured output schema for the router LLM
class RouterOutput(BaseModel):
    path: str = Field(description="Chosen path: hybrid, sql_query, sql_retrieve, web_search")
    confidence: float = Field(description="Confidence score 0.0-1.0")


_routing_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Routing Engine for the CNPI Hybrid RAG System.

Your responsibility is ONLY to decide which retrieval path should answer the user's question.

Do NOT answer the question.
Do NOT rewrite the question.
Do NOT generate SQL.
Do NOT retrieve documents.

Return ONLY the selected path and a confidence score.

-----------------------------------
Available Paths
-----------------------------------

1. sql_query
2. sql_retrieve
3. web_search
4. hybrid

-----------------------------------
Routing Rules
-----------------------------------

Choose "sql_query" ONLY for very specific structured queries regarding:
- Last N notices (e.g., "last 5 notice", "latest notices")
- Last/Latest news (e.g., "last news", "recent news")
- Total counts of specific entities like teachers (e.g., "total teacher", "how many teachers")

If the question is strictly about these few specific topics,
choose:

sql_query

-----------------------------------

Choose "sql_retrieve" for ANY OTHER single college-related question.
This is the default path for almost all college knowledge base queries.

Examples:
• teacher details (name, phone, email, designation, department)
• department details (name, code, head, shift)
• exact lookup questions (e.g., "who is the head of CSE?", "phone number of Rahim Sir")
• admission process
• scholarship information
• class routine explanation
• exam rules
• notice explanation
• semester information
• laboratory information
• any other general information about the college

If it's a general question about the college, teachers, departments, rules, or any information NOT strictly covered by the few sql_query cases, OR if the user is just saying a greeting or smalltalk (e.g. "hi", "hello", "thanks"),
choose:

sql_retrieve

-----------------------------------

Choose "web_search" when the question is NOT about the college knowledge base and requires external or up-to-date information.

Examples:

• world news
• current weather
• programming questions
• Python
• AI
• Bangladesh news
• Google
• Stack Overflow
• OpenAI
• latest technologies
• current events
• information outside the college database

-----------------------------------

Choose "hybrid" ONLY when answering requires multiple independent retrieval paths or multiple college-related questions.

Examples:

• Who is the head of CSE and what is the admission process?

• Give the phone number of Rahim Sir and explain the department.

• Compare Computer Technology and Civil Technology departments.

• Show all departments and explain their admission requirements.

• Tell me today's AI news and also who is the principal of CNPI.

• Any question containing multiple independent intents that should be decomposed into separate sub-questions.

-----------------------------------
Confidence

Return confidence between 0.0 and 1.0.

Use high confidence (0.90-1.00) when the routing decision is obvious.

Use medium confidence (0.70-0.89) when one path is clearly preferable but some ambiguity exists.

Use lower confidence (<0.70) only when the intent is genuinely ambiguous.

-----------------------------------
Output Format

Return ONLY valid JSON.

{{
  "path": "sql_query | sql_retrieve | web_search | hybrid",
  "confidence": 0.97
}}"""),
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

    
    
    result = routing_chain.invoke({"rewritten_query": query})

        # Normalize to canonical PathName values
    path_map: dict[str, str] = {
            "hybrid": "hybrid",
            "sql_query": "sql_query",
            "sql_retrieve": "sql_retrieve",
            "web_search": "web_search",
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