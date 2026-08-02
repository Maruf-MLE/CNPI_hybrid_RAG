"""
SQL Query Response Node - Phase 2
===================================

Generate final answer from database context using LLM.

Flow: sql_query.{optimized_context, raw_context} + user_input â†’ sql_query.final_answer
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


_response_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant answering user questions based strictly on database search results.

Use ONLY the provided context. Do not hallucinate or add outside information.
Answer clearly in the language of the user question (e.g., Bengali if the user asked in Bengali).

FORMATTING & PRESENTATION - VERY IMPORTANT:
- **BEAUTIFUL FORMATTING & EMOJIS**: You MUST format the answer beautifully to make it visually appealing.
- Use relevant emojis generously but appropriately (e.g., 🎓, 🏫, 👨🏫, 👩🏫, 📞, 📧, 🕒, 💡, ✨, 📌, 📚, etc.).
- Use bullet points (• or ✅) or numbered lists to present information clearly.
- Use **bold text** to highlight important names, designations, phone numbers, or key information.
- Add clear paragraph breaks to separate different pieces of information.

HONORIFIC RULE — VERY IMPORTANT:
Whenever you mention a person who is a Principal, Vice Principal, Chief Instructor (CI),
Instructor, or Teacher, you MUST address them with "Sir" (or "ম্যাডাম" for female teachers)
as a sign of respect. This applies EVERY time the person's name is mentioned.
- For male: add "Sir" after the name (e.g., "Md. Rejuanul Arefin Sir")
- For female: add "ম্যাডাম" after the name (e.g., "Mosa: Roshana Khatun ম্যাডাম")
- Keep "Sir" in English (do not write "স্যার").
- ALWAYS use "Sir"/"ম্যাডাম" — never omit it when mentioning a teacher/CI/Principal by name.

Context:
{context}"""),
    ("human", "User Question: {user_input}")
])


def sql_query_response_node(state: RAGState) -> dict:
    """Generate final answer from database context."""
    llm = get_llm()
    chain = _response_prompt | llm

    sql_query_state = state.get("sql_query", {})
    user_input = state.get("user_input", "")
    context = sql_query_state.get("optimized_context", "") or sql_query_state.get("raw_context", "")

    if not context:
        return {
            "sql_query": {
                **sql_query_state,
                "final_answer": "No database information was found for your query."
            }
        }

    try:
        response = chain.invoke({
            "context": context,
            "user_input": user_input
        })

        final_answer = extract_content(response)
        if isinstance(final_answer, list):
            final_answer = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in final_answer)
            
        final_answer = final_answer.strip()

        return {
            "sql_query": {
                **sql_query_state,
                "final_answer": final_answer
            }
        }
    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        print(error_msg)

        return {
            "sql_query": {
                **sql_query_state,
                "final_answer": f"Error: {error_msg}. Please try again."
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "user_input": "CST-à¦  à¦•à¦¤à¦œà¦¨ à¦¶à¦¿à¦•à§ à¦·à¦• à¦†à¦›à§‡à¦¨?",
        "sql_query": {
            "raw_context": "total_teachers: 10\nshort_code: CST\nname_en: Computer Science and Technology"
        }
    }

    result = sql_query_response_node(state)
    print("Response Node Result:")
    print(result)