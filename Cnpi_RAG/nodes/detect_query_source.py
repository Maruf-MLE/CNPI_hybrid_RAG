"""
Query Source Detection Node
============================

Automatically detect query source from state metadata or external indicators.
"""

from typing import Dict, Any
from state import RAGState


def detect_query_source_node(state: RAGState) -> Dict[str, Any]:
    """
    Detect query source if not already set.
    
    Priority:
    1. Explicit query_source in state
    2. Check metadata fields
    3. Default to "web"
    """
    
    # যদি already set থাকে, তাহলে সেটাই use করো
    if "query_source" in state and state["query_source"]:
        return {"query_source": state["query_source"]}
    
    # Check for telegram-specific indicators
    # তোমার system এ যদি telegram থেকে কোনো special metadata আসে
    metadata = state.get("metadata", {})
    
    # Example indicators
    if metadata.get("platform") == "telegram":
        return {"query_source": "telegram"}
    
    if metadata.get("chat_id"):  # Telegram chat ID থাকলে
        return {"query_source": "telegram"}
    
    if metadata.get("from_bot") == "telegram":
        return {"query_source": "telegram"}
    
    # Check user_input for telegram-style patterns (optional)
    user_input = state.get("user_input", "")
    
    # যদি query তে telegram-specific markers থাকে
    if user_input.startswith("/"):  # Telegram commands
        return {"query_source": "telegram"}
    
    # Default to web
    return {"query_source": "web"}


# Example usage
if __name__ == "__main__":
    # Test 1: Explicit source
    state1 = {
        "user_input": "CST er routine dao",
        "query_source": "telegram"
    }
    result1 = detect_query_source_node(state1)
    print("Test 1:", result1)  # {"query_source": "telegram"}
    
    # Test 2: Metadata detection
    state2 = {
        "user_input": "Show routine",
        "metadata": {
            "platform": "telegram",
            "chat_id": 123456
        }
    }
    result2 = detect_query_source_node(state2)
    print("Test 2:", result2)  # {"query_source": "telegram"}
    
    # Test 3: Default
    state3 = {
        "user_input": "Show routine"
    }
    result3 = detect_query_source_node(state3)
    print("Test 3:", result3)  # {"query_source": "web"}
