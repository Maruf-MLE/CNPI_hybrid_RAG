import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.db_utils import execute_query

# Check CI consolidated list documents
result = execute_query(
    "SELECT content, meta FROM documents WHERE doc_type = 'ci_consolidated_list' LIMIT 3",
    fetch=True
)
print('CI Consolidated List documents:')
for r in result:
    print(f'Content: {r["content"][:300]}')
    print(f'Meta: {r["meta"]}\n')

# Check CST department CI data
cst_ci = execute_query(
    "SELECT content, meta FROM documents WHERE (content ILIKE '%CST%' AND content ILIKE '%chief%') OR (meta::text ILIKE '%CST%' AND doc_type = 'ci_consolidated_list')",
    fetch=True
)
print('\n\nCST Chief Instructor data:')
for r in cst_ci:
    print(f'Content: {r["content"][:300]}')
    print(f'Meta: {r["meta"]}\n')
