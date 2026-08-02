"""
SQL Query Generation Prompt
============================

Template for generating SQL queries from natural language.
Used by sql_query_create node in Phase 2.
"""

SQL_GENERATION_PROMPT = """
You are a SQL query generation expert for a college database.

DATABASE STRUCTURE INFORMATION:
{database_info}

NATURAL LANGUAGE QUERY: "{user_query}"

Your task is to generate an SQL query that retrieves information related to the query.

Requirements:
1. Return ONLY the SQL query as a code block (```sql ... ```)
2. DO NOT include explanation, conversational text, or other content
3. Use safe parameterized queries (placeholder values should be replaced)
4. For text fields, use LIKE with appropriate wildcards
5. Handle NULL values gracefully
6. Order results by date and priority if applicable

Example format:
```sql
SELECT * FROM table_name WHERE column LIKE %s LIMIT 1;
```

Note: Placeholders should be in the format %s for PostgreSQL. Do not include Python code or other explanations.
"""


def get_sql_generation_prompt(db_info: str, user_query: str) -> str:
    """
    Get SQL generation prompt with current context.

    Parameters:
        db_info (str): Database schema information
        user_query (str): User's natural language query

    Returns:
        str: Complete prompt for LLM
    """
    return SQL_GENERATION_PROMPT.format(
        database_info=db_info,
        user_query=user_query
    )


SUPPORT_CHECK_PROMPT = """
You are a validation expert. You need to determine if an answer is supported by the provided context.

CONTEXT PROVIDED:
{context}

ANSWER PROVIDED:
{answer}

ANALYSIS:
1. Does the answer mention dates?
2. Is the information factually correct based on context?
3. Are there flagship/priority recent items?

Your task: Return "SUPPORTED" if the answer has:

- Verifiable dates (recent/flagship/priority items mentioned)
- Clear context connection
- No hallucinations

Return "UNSUPPORTED" if:
- No dates present
- Information cannot be verified from context
- Unsubstantiated claims
- Generic responses without specific details

Return "NEED_MORE_INFO" if:
- Information is missing or incomplete
- Requires clarification to answer accurately
"""

def get_support_check_prompt(context: str, answer: str) -> str:
    """
    Get support check prompt.

    Parameters:
        context (str): Retrieved context
        answer (str): Generated answer

    Returns:
        str: Complete prompt for LLM
    """
    return SUPPORT_CHECK_PROMPT.format(
        context=context,
        answer=answer
    )


REWRITE_QUERY_PROMPT = """
You are a query rewriter for a college information system.

Original Query: "{user_query}"

Rewrite the query to make it more suitable for:
1. Database searches
2. Semantic retrieval
3. Understanding user intent

Requirements:
- Keep the core meaning
- Make it more specific and clear
- Remove conversational fillers
- Standardize terminology

Rewritten Query: {rewritten_query}
"""

def get_rewrite_query_prompt(user_query: str) -> str:
    """
    Get query rewrite prompt.

    Parameters:
        user_query (str): Original user query

    Returns:
        str: Complete prompt for LLM
    """
    return REWRITE_QUERY_PROMPT.format(
        user_query=user_query
    )


METADATA_SEARCH_PROMPT = """
You are a metadata search optimization expert.

User Query: "{user_query}"

Database tables and columns:
{table_info}

Your task: Generate a search query in natural language that would match relevant rows in the database.

Return the NATURAL LANGUAGE search string only.
""""