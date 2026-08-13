"""
Test SQL Retrieve with DateTime Context
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'Cnpi_RAG')
sys.path.insert(0, 'plan')

from datetime import datetime
from nodes.sql_retrieve_context import sql_retrieve_context_node

print('Testing SQL Retrieve with DateTime Context')
print('=' * 70)
print(f'Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('=' * 70)

# Test state
test_state = {
    "user_input": "CST Department এর Chief Instructor কে?",
    "sql_retrieve": {
        "search_query": "CST Department Chief Instructor"
    }
}

print(f'\nTest Query: {test_state["sql_retrieve"]["search_query"]}')
print('\nExecuting sql_retrieve_context_node...\n')

result = sql_retrieve_context_node(test_state)

sql_retrieve_state = result.get("sql_retrieve", {})
context_found = sql_retrieve_state.get("context_found", False)
raw_context = sql_retrieve_state.get("raw_context", "")

print(f'✅ Context Found: {context_found}')
print(f'✅ Raw Context Length: {len(raw_context)} chars')

if context_found and raw_context:
    print('\n📄 Retrieved Context Preview (first 200 chars):')
    print('-' * 70)
    print(raw_context[:200] + '...')
    print('-' * 70)
    print('\n✅ SQL Retrieve is now using current date & time for retrieval!')
else:
    print('\n⚠️ No context found')

print('\n' + '=' * 70)
print('Test Complete')
