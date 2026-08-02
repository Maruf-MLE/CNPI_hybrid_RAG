"""
SQL Retrieve Response Node - Phase 3
================================

Generate final answer from retrieved context using LLM.

Flow: sql_retrieve.context_with_meta -> sql_retrieve.final_answer
"""

import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState
from utils.llm_utils import get_llm, extract_content
from langchain_core.prompts import ChatPromptTemplate


_RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a friendly, helpful assistant for the students of Chapainawabganj Polytechnic Institute (CNPI).
You answer their questions using the retrieved context in a way that is EASY for students to understand.

CRITICAL INSTRUCTIONS — LANGUAGE & STYLE:
1. You MUST answer in Bengali language (বাংলা ভাষায়) with very SIMPLE, easy-to-understand words —
   like a friendly senior student or teacher explaining to a junior student.
2. DO NOT translate technical terms, names, or designations into Bengali. Keep words like Shift, Day,
   Morning, Chief Instructor, CI, CST, ENT, ET, RAC, FT, MT, CNPI, Tech, Department, Phone, etc., in
   ENGLISH. (e.g. write "CST Department-এর Day Shift-এর Chief Instructor হলেন..." instead of translating).
3. NEVER include conversational preambles or fluff (e.g., "Based on the retrieved context...",
   "Here is the answer..."). Just give the direct answer.
4. Use short, clear sentences. Avoid complex or formal vocabulary that a student might struggle with.
   If a long sentence can be broken into two short ones, do it.

FORMATTING & PRESENTATION - VERY IMPORTANT:
5. **BEAUTIFUL FORMATTING & EMOJIS**: You MUST format the answer beautifully to make it visually appealing.
   - Use relevant emojis generously but appropriately (e.g., 🎓, 🏫, 👨🏫, 👩🏫, 📞, 📧, 🕒, 💡, ✨, 📌, 📚, etc.).
   - Use bullet points (• or ✅) or numbered lists to present information clearly.
   - Use **bold text** to highlight important names, designations, phone numbers, or key information.
   - Add clear paragraph breaks to separate different pieces of information.

HONORIFIC RULE — VERY IMPORTANT:
6. Whenever you mention a person who is a Principal, Vice Principal, Chief Instructor (CI),
   Instructor, or Teacher, you MUST address them with "Sir" (or "ম্যাডাম" for female teachers)
   as a sign of respect. This applies EVERY time the person's name is mentioned.
   - For male: add "Sir" after the name (e.g., "Md. Rejuanul Arefin Sir", "Md. Subel Ali Sir")
   - For female: add "ম্যাডাম" after the name (e.g., "Mosa: Roshana Khatun ম্যাডাম")
   - Examples:
     WRONG: "CST Department-এর Chief Instructor হলেন Md. Rejuanul Arefin।"
     RIGHT: "CST Department-এর Chief Instructor হলেন Md. Rejuanul Arefin Sir।"
     WRONG: "Principal হলেন Md. Omar Farooq।"
     RIGHT: "Principal হলেন Md. Omar Farooq Sir।"
     WRONG: "Vice Principal Salim Ahmed এর ফোন নম্বর..."
     RIGHT: "Vice Principal Salim Ahmed Sir এর ফোন নম্বর..."
   - Keep "Sir" in English (do not write "স্যার").
   - ALWAYS use "Sir" — never omit it when mentioning a teacher/CI/Principal by name.

ANSWER DETAIL:
7. Try to include ALL relevant details from the context that directly answer the question
   (dates, names, phone numbers, designations, etc.). Be as detailed as the context allows.
8. BUT do NOT add extra information that was NOT asked for and NOT relevant — no unnecessary filler,
   no off-topic facts. Give exactly what the student needs, nothing more.

READING RULES — VERY IMPORTANT:
9. Read EVERY context block carefully. The answer may be inside a LARGER block of text that contains
   lists, tables, or multiple Q&A pairs. Scan the ENTIRE content, not just the first few lines.
10. If the user asks about a specific entity (e.g., ENT Department) and the context contains a LIST that
    includes that entity, extract and present the matching entry from that list.
11. If the EXACT entity the user asked about is NOT found in the context, but the context contains RELATED
    information (e.g., a full list of all departments/CIs), then:
    - Clearly state that the specific entity was not found.
    - ALSO present the closest related information that IS available (e.g., "ENT Department-ের কোনো
      Chief Instructor তালিকায় নেই, তবে অন্যান্য Department-ের Day Shift-ের Chief Instructor হলেন: ...")
    - Do NOT just say "তথ্য পাওয়া যায়নি" and stop — always share whatever relevant information exists.
12. If absolutely NO related information exists in any context block, only then say in Bengali that the
    information was not found.

FOLLOW-UP QUESTION — MANDATORY:
13. At the VERY END of your answer, you MUST add a friendly follow-up question asking if the student
    needs any more help. Use a warm, student-friendly tone. Examples (adapt to the language of the question):
    - "আমি আর কীভাবে আপনাকে সাহায্য করতে পারি?"
    - "আর কিছু জানতে চান?"
    - "এছাড়া আর কোনো বিষয়ে জানতে চাইলে বলুন, আমি সাহায্য করতে প্রস্তুত।"
    Always end with this kind of follow-up. Never skip it.

Answer:
"""),
    ("human", "User Query: {user_query}\n\nRetrieved Context:\n{context}")
])


def sql_retrieve_response_node(state: RAGState) -> Dict[str, Any]:
    """Generate final response from retrieved context."""
    
    # Get the shared LLM instance
    llm = get_llm()
    chain = _RESPONSE_PROMPT | llm

    sql_retrieve_state = state.get("sql_retrieve", {})
    # Use normalized query instead of raw user input
    user_query = state.get("normalized_query") or state.get("rewritten_query") or state.get("user_input", "")
    context = sql_retrieve_state.get("context_with_meta", "")

    try:
        if not context:
            return {
                "sql_retrieve": {
                    **sql_retrieve_state,
                    "final_answer": "দুঃখিত, আপনার প্রশ্নের সাথে সম্পর্কিত কোনো তথ্য পাওয়া যায়নি। আমি আর কীভাবে আপনাকে সাহায্য করতে পারি?"
                }
            }

        response = chain.invoke({
            "user_query": user_query,
            "context": context
        })

        answer = extract_content(response)
        if isinstance(answer, list):
            # Gemini sometimes returns a list of content blocks
            answer = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in answer)
            
        answer = answer.strip()
        
        if not answer:
            raise ValueError("No response generated")

        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "final_answer": answer
            }
        }
    except Exception as e:
        error_msg = f"Response generation error: {str(e)}"
        print(error_msg)
        
        return {
            "sql_retrieve": {
                **sql_retrieve_state,
                "final_answer": "উত্তর তৈরি করতে সমস্যা হয়েছে। দয়া করে আবার চেষ্টা করুন। আর কিছু জানতে চাইলে বলুন।"
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    state = {
        "user_input": "What facilities are available at the college?",
        "sql_retrieve": {
            "context_with_meta": "Context for: 'college facilities'\nDate: 2024-01-15\nPriority: High\nInformation:\nThe college has a library, computer lab, sports ground, and auditorium."
        }
    }

    result = sql_retrieve_response_node(state)
    print("Retrieve Response Result:")
    print(result)