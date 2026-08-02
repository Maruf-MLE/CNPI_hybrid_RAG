"""
CNPI RAG System - Main Entry Point
==================================

This is the main entry point for the Comprehensive Non-National Educational
Public Institution Hybrid RAG System.

System Architecture:
- Multi-path retrieval system (SQL Query, SQL Retrieve, Web Search, Hybrid)
- LangGraph for flow control and state management
- Modular node-based architecture
- Support validation and retry mechanisms

Current Implementation: Phase 1 (Foundation + Entry + Router)
"""

import os
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent
os.chdir(project_root)

from nodes.entry import rewrite_query_node
from nodes.router import llm_decide_path_node
from graph import build_phase1_graph


def initialize_system():
    """
    Initialize the RAG system configuration.
    """
    print("🚀 CNPI RAG System Initializing...")
    print("=" * 50)

    # Check for required environment variables
    required_env_vars = [
        "GROQ_API_KEY",
        "DB_HOST",
        "DB_NAME",
        "DB_USER"
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("   Some features may not work correctly.")
    else:
        print("✓ All required environment variables are set")

    # Load API key if present
    if os.getenv("GROQ_API_KEY"):
        print("✓ LLM API configured")
    else:
        print("⚠️  Groq API key not found")

    print("=" * 50)


def process_query(user_query: str, path: str = None, confidence: float = None):
    """
    Process a user query through the RAG system.

    Parameters:
        user_query (str): User's question or query
        path (str, optional): Specific path to use (sql_query, sql_retrieve, web_search, hybrid)
        confidence (float, optional): Confidence score for routing (0.0-1.0)

    Returns:
        dict: Processing result with decided path, confidence, and final answer
    """
    # Initial state
    initial_state = {
        "user_input": user_query,
        "rewritten_query": "",
        "decided_path": "",
        "confidence_score": 0.0,
    }

    # Build graph (in production, build once and cache)
    graph = build_phase1_graph()

    # Process query
    result = graph.invoke(initial_state)

    return result


def example_interactions():
    """
    Example of system interactions for different query types.
    """
    print("\n📋 RAG System Examples")
    print("=" * 50)

    examples = [
        {
            "query": "What is the full name of the principal responsible for administrative matters?",
            "desc": "Simple fact retrieval"
        },
        {
            "query": "What notices were published this week in the notice board?",
            "desc": "Query with temporal constraint + priority"
        },
        {
            "query": "Define what a 'Faculty Quality Assessment' is and when it's conducted",
            "desc": "Conceptual question"
        },
        {
            "query": "Who is the head of the CSE department and when did they join?",
            "desc": "Complex multi-intent query"
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\nExample {i}: {example['desc']}")
        print(f"Query: {example['query']}")
        print("-" * 50)

        result = process_query(example['query'])
        print(f"→ Decided Path: {result.get('decided_path', 'Not decided')}")
        print(f"→ Confidence: {result.get('confidence_score', 0):.2f}")
        print(f"→ Rewritten Query: {result.get('rewritten_query', 'N/A')}")


def main():
    """
    Main entry point for the system.
    """
    # Initialize system
    initialize_system()

    # Run examples
    example_interactions()

    # Interactive mode (optional)
    print("\n💬 Interactive Mode (Enter 'quit' to exit)")
    print("=" * 50)

    while True:
        user_query = input("\n👤 Your query: ").strip()

        if user_query.lower() in ['quit', 'exit', 'q']:
            print("👋 Exiting system...")
            break

        if user_query:
            result = process_query(user_query)
            print(f"\n🎯 Decided Path: {result.get('decided_path', 'Not decided')}")
            print(f"📊 Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"🤖 Rewritten: {result.get('rewritten_query', 'N/A')}")


if __name__ == "__main__":
    main()