import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.db_utils import execute_query

# Check documents in database
result = execute_query('SELECT COUNT(*) as total, doc_type FROM documents GROUP BY doc_type', fetch=True)
print('Documents in database:')
for r in result:
    print(f'  {r["doc_type"]}: {r["total"]}')

total = sum(r["total"] for r in result) if result else 0
print(f'\nTotal documents: {total}')

# Check for CST department data
cst_result = execute_query(
    "SELECT doc_type, topic, department FROM documents WHERE department = 'CST' LIMIT 5", 
    fetch=True
)
print('\nSample CST documents:')
for r in cst_result:
    print(f'  Type: {r["doc_type"]}, Topic: {r.get("topic", "N/A")[:50] if r.get("topic") else "N/A"}')

# Check for Chief Instructor data
ci_result = execute_query(
    "SELECT content, meta FROM documents WHERE content ILIKE '%chief instructor%' LIMIT 3",
    fetch=True
)
print('\nChief Instructor data:')
for r in ci_result:
    print(f'  Content: {r["content"][:100]}...')
    print(f'  Meta: {r["meta"]}')
