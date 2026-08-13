"""
Trace LLM calls to identify bottlenecks
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'Cnpi_RAG')
sys.path.insert(0, 'plan')

# Trace করার জন্য wrapper function
original_get_llm = None
call_log = []

def trace_llm_calls():
    from utils import llm_utils
    global original_get_llm
    original_get_llm = llm_utils.get_llm
    
    call_count = {'count': 0}
    
    def traced_get_llm(*args, **kwargs):
        import traceback
        import time
        call_count['count'] += 1
        stack = traceback.extract_stack()
        caller = stack[-2]
        filename = caller.filename.split('nodes\\')[-1] if 'nodes' in caller.filename else caller.filename
        
        start = time.time()
        result = original_get_llm(*args, **kwargs)
        elapsed = time.time() - start
        
        log_entry = {
            'num': call_count['count'],
            'file': filename,
            'line': caller.lineno,
            'func': caller.name,
            'time': elapsed
        }
        call_log.append(log_entry)
        print(f"  [{call_count['count']}] LLM Call from: {filename}:{caller.lineno} - {caller.name}() [{elapsed:.2f}s]")
        return result
    
    llm_utils.get_llm = traced_get_llm
    return call_count

# Start tracing
print('=' * 70)
print('Tracing LLM Calls in RAG Pipeline')
print('=' * 70)

call_count = trace_llm_calls()

# Simulate a typical query path
print('\nTest Query: "CST department er routine dao"')
print('Expected Path: sql_retrieve')
print('=' * 70)

from nodes.entry import rewrite_query_node
from nodes.entity_normalizer import entity_normalizer_node
from nodes.router import llm_decide_path_node
from nodes.sql_retrieve_check import sql_retrieve_check_node

state = {
    'user_input': 'CST department er routine dao',
    'messages': []
}

print('\n[Phase 1] Entry & Routing')
print('-' * 70)
state.update(rewrite_query_node(state))
state.update(entity_normalizer_node(state))
state.update(llm_decide_path_node(state))

print(f'\nDecided Path: {state.get("decided_path")}')
print(f'Confidence: {state.get("confidence_score")}')

print('\n[Phase 3] SQL Retrieve Check')
print('-' * 70)
state.update(sql_retrieve_check_node(state))

print('\n' + '=' * 70)
print(f'TOTAL LLM CALLS: {call_count["count"]}')
print('=' * 70)

print('\nDetailed Breakdown:')
print('-' * 70)
total_time = sum(log['time'] for log in call_log)
for log in call_log:
    pct = (log['time'] / total_time * 100) if total_time > 0 else 0
    print(f"{log['num']}. {log['file']:30s} {log['func']:25s} {log['time']:6.2f}s ({pct:5.1f}%)")

print(f"\nTotal LLM Time: {total_time:.2f}s")
print('=' * 70)
