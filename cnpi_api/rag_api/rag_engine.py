"""
RAG Engine Wrapper
==================

Compiles the LangGraph ONCE (at import time) and exposes a single
``run_rag()`` function that the Django views can call.

This avoids re-compiling the graph on every HTTP request, which would
be extremely slow.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compile the graph lazily so import errors don't crash Django startup.
# ---------------------------------------------------------------------------

_compiled_graph = None


def _get_compiled_graph():
    """Return the compiled LangGraph, building it on first call."""
    global _compiled_graph
    if _compiled_graph is None:
        logger.info("Compiling RAG graph (first call)...")
        from Cnpi_RAG.graph import app as graph_app

        _compiled_graph = graph_app.compile()
        logger.info("RAG graph compiled successfully.")
    return _compiled_graph


def run_rag(user_input: str, chat_history: list | None = None) -> dict:
    """Run the full RAG pipeline for a single user question.

    Parameters:
        user_input:   the raw user question for this turn.
        chat_history:  list of langchain BaseMessage objects from prior turns
                       (HumanMessage / AIMessage). Pass [] or None for the
                       first turn.

    Returns:
        dict with keys:
            final_answer     — the bot's answer text
            answer_status    — "found" | "not_found" | "need_more_info" | "pending"
            decided_path     — which RAG path was used
            rewritten_query  — the rewritten / normalized query
            messages          — updated chat history (list of BaseMessage)
            debug_info       — extra debug fields (depth, sub-queries, etc.)
    """
    from plan.state import new_rag_state

    compiled = _get_compiled_graph()

    initial_state = new_rag_state(
        user_input=user_input,
        messages=chat_history or [],
    )

    logger.info("Invoking graph for user_input: %s", user_input[:80])
    result_state = compiled.invoke(initial_state)

    # ---- Extract final_answer (top-level or nested) ----
    final_ans = result_state.get("final_answer", "")
    decided_path = result_state.get("decided_path", "")

    if not final_ans and decided_path:
        path_state = result_state.get(decided_path, {})
        if isinstance(path_state, dict):
            final_ans = path_state.get("final_answer", "")

    # ---- Collect debug info ----
    debug_info = {
        "rewritten_query": result_state.get("rewritten_query", ""),
        "normalized_query": result_state.get("normalized_query", ""),
        "confidence_score": result_state.get("confidence_score", 0.0),
        "answer_status": result_state.get("answer_status", "pending"),
    }

    if decided_path == "hybrid":
        hybrid_data = result_state.get("hybrid", {})
        debug_info["hybrid_depth"] = hybrid_data.get("depth")
        debug_info["total_sub_queries"] = hybrid_data.get("total_sub_q")
        debug_info["sub_query_list"] = hybrid_data.get("sub_query_list", [])

    # ---- Updated chat history ----
    updated_messages = list(result_state.get("messages", []))
    
    from langchain_core.messages import AIMessage
    # Append the bot's response to the history so it's available for the next turn
    updated_messages.append(
        AIMessage(content=final_ans or "(কোনো উত্তর নেই)")
    )

    return {
        "final_answer": final_ans or "",
        "answer_status": result_state.get("answer_status", "pending"),
        "decided_path": decided_path,
        "rewritten_query": debug_info.get("rewritten_query", ""),
        "messages": updated_messages,
        "debug_info": debug_info,
    }


def get_graph_visualization() -> str:
    """Return a text representation of the compiled graph (for debugging)."""
    compiled = _get_compiled_graph()
    return str(compiled)
