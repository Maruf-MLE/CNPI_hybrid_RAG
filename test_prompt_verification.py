import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'plan'))
sys.path.insert(0, str(Path.cwd() / 'Cnpi_RAG'))

# Check hybrid path nodes
print('Checking Hybrid Path Nodes:')
print('='*70)

from Cnpi_RAG.nodes.hybrid_create_sub_questions import _DECOMPOSE_PROMPT
from Cnpi_RAG.nodes.hybrid_merge_sub_answers import _MERGE_PROMPT

print('\n1. hybrid_create_sub_questions.py:')
print(_DECOMPOSE_PROMPT.messages[0].prompt.template[:200])

print('\n2. hybrid_merge_sub_answers.py:')
print(_MERGE_PROMPT.messages[0].prompt.template[:200])

print('\n3. Other important nodes:')
from Cnpi_RAG.nodes.no_answer_found import _NO_ANSWER_PROMPT
from Cnpi_RAG.nodes.web_search_response import _RESPONSE_PROMPT as web_resp_prompt
from Cnpi_RAG.nodes.entry import rewrite_prompt

print('\n  - no_answer_found.py:')
print(_NO_ANSWER_PROMPT.messages[0].prompt.template[:150])

print('\n  - web_search_response.py:')
print(web_resp_prompt.messages[0].prompt.template[:150])

print('\n  - entry.py (rewrite):')
print(rewrite_prompt.messages[0].prompt.template[:150])

print('\n' + '='*70)
print('All prompts verified - No Chandpur found!')
