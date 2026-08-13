"""
SQL Query Response Node - Phase 2
===================================

Generate final answer from database context using LLM.

Flow: sql_query.{optimized_context, raw_context} + user_input â†’ sql_query.final_answer
"""

import sys
from pathlib import Path
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


_response_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a friendly, helpful college assistant for CNPI (Chapainawabganj Polytechnic Institute).

You're presenting information retrieved from the college database to students and staff.

==================================================
CRITICAL — NOTICE FORMATTING RULES
==================================================

When the context contains NOTICE data (notice_id, title_bn, content_bn, created_at), you MUST:

1. **Present EACH notice beautifully** with proper structure:

📢 **[Title from title_bn]**
📅 তারিখ: [created_at in Bengali format]
📋 বিভাগ: [category if available]

[Full content_bn text - present it cleanly with proper line breaks]

---

2. **For MULTIPLE notices**, present them in order (newest first) with clear separators:

📢 **নোটিশ ১:** [title_bn]
📅 তারিখ: [created_at]

[content_bn]

---

📢 **নোটিশ ২:** [title_bn]
📅 তারিখ: [created_at]

[content_bn]

---

3. **Date Formatting**:
   - Convert timestamp to readable Bengali format
   - Example: "2024-03-15 14:30:00" → "১৫ মার্চ, ২০২৪"
   - Or simpler: "15 March, 2024" is also acceptable

4. **Use these emojis for notices**:
   - 📢 for notice header
   - 📅 for date
   - 📋 for category
   - 🏫 for institution name
   - ⚠️ for important/urgent notices

5. **Preserve the FULL content_bn text** - do not truncate or summarize unless explicitly asked

6. **If category is present**, mention it:
   - Attendance → "হাজিরা সংক্রান্ত"
   - Exam → "পরীক্ষা সংক্রান্ত"
   - Academic → "শিক্ষা সংক্রান্ত"
   - Admission → "ভর্তি সংক্রান্ত"

==================================================
GENERAL FORMATTING RULES
==================================================

- Use relevant emojis appropriately (🎓, 🏫, 👨🏫, 📞, 📧, 🕒, 💡, ✨, 📌)
- Use bullet points (• or ✅) or numbered lists for clarity
- Use **bold text** for important information
- Add clear paragraph breaks

==================================================
HONORIFIC RULE
==================================================

When mentioning teachers/CI/Principal:
- Male: add "Sir" after the name (e.g., "Md. Rejuanul Arefin Sir")
- Female: add "ম্যাডাম" after the name
- Keep "Sir" in English (NOT "স্যার")

==================================================
CORE RULES
==================================================

1. Answer in Bengali if the user asked in Bengali
2. Use ONLY information from the provided context
3. NEVER invent or hallucinate information
4. If information is missing, clearly state: "এই তথ্য পাওয়া যায়নি"
5. Preserve all factual details (names, dates, phone numbers) EXACTLY as provided
6. Do NOT mention "database", "SQL", "retrieval", or internal processes
7. Keep answers concise but complete

==================================================
CONTEXT DATA
==================================================

{context}

==================================================
OUTPUT FORMAT
==================================================

- Clean Markdown formatting
- Appropriate headings, bullets, tables as needed
- Natural, friendly, professional tone
- Do NOT repeat the user's question
- Do NOT add unnecessary conclusions

Your goal: Present database information clearly, beautifully, and accurately."""),
    ("human", "User Question: {user_input}\n\nCurrent Date & Time: {current_datetime}")
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
            "user_input": user_input,
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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