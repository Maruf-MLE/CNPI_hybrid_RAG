"""
SQL Query Row Check & Optimized Node - Phase 2
===============================================

Check row count and optimize context for LLM migration. This handles the conditional
routing: Row=0 → SQL Retrieve path, Row=1+ → continue with response.

Flow: sql_query.row_count → sql_query.optimized_context (with fallback)
"""

from typing_extensions import TypedDict

class SQLQueryRowCheckState(TypedDict, total=False):
    sql_query: dict

def sql_query_row_check_and_optimize_node(state: SQLQueryRowCheckState) -> dict:
    """Check row count and optimize context.

    Logic:
    - Row=0 → SQL Retrieve path (fallback)
    - Row=1 → Continue with direct answer
    - Row=1+ → Continue with multiple answers
    - Row check → Optimized context with priority sorting
    """
    sql_query_state = state.get("sql_query", {})
    row_count = sql_query_state.get("row_count", 0)
    raw_context = sql_query_state.get("raw_context", "")

    if row_count == 0:
        # Fallback to SQL Retrieve path
        return {
            "sql_query": {
                **sql_query_state,
                "final_answer": None,  # Signal to route to SQL Retrieve
                "sql_retrieve": {
                    "raw_context": "",
                    "context_found": False
                }
            }
        }

    elif row_count == 1:
        # Single row - create optimized context directly
        optimized_context = format_optimized_context([raw_context], ["priority_high"])

        return {
            "sql_query": {
                **sql_query_state,
                "optimized_context": optimized_context
            }
        }

    else:
        # Multiple rows - create combaded optimized context
        optimized_context = format_optimized_context(
            [raw_context],
            ["priority_high", "date_important"]
        )

        return {
            "sql_query": {
                **sql_query_state,
                "optimized_context": optimized_context
            }
        }

def format_optimized_context(rows_data, importance_tags):
    """
    Format context with priority and date information.

    Parameters:
        rows_data (list): List of formatted row strings
        importance_tags (list): Tags indicating importance level

    Returns:
        str: Formatted optimized context
    """
    lines = []

    # Add importance header
    if importance_tags:
        lines.append("### Context Details")
        tags_str = ", ".join(importance_tags)
        lines.append(f"### Importance: {tags_str}")
        lines.append("")

    # Format rows
    for idx, row_text in enumerate(rows_data, 1):
        lines.append(f"--- Row {idx} ---")
        lines.append(row_text)
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":

    # Test format_optimized_context helper
    sample_rows = ["id: 1\nname: CSE Department", "id: 2\nname: EEE Department"]
    sample_tags = ["priority_high", "date_important"]

    context = format_optimized_context(sample_rows, sample_tags)
    print("Optimized Context:")
    print(context)

    # Test node with multiple rows
    state = {
        "sql_query": {
            "row_count": 2,
            "raw_context": "id: 1\nname: John\ndesignation: Professor"
        }
    }

    result = sql_query_row_check_and_optimize_node(state)
    print("\nRow Check Node (multi-row):")
    print(result)

    # Test node with zero rows (fallback path)
    state_empty = {
        "sql_query": {
            "row_count": 0,
            "raw_context": ""
        }
    }

    result_empty = sql_query_row_check_and_optimize_node(state_empty)
    print("\nRow Check Node (zero rows - fallback):")
    print(result_empty)