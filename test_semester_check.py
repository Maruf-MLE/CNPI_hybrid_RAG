import sys
from pathlib import Path

current_dir = Path.cwd()
sys.path.insert(0, str(current_dir / 'plan'))
sys.path.insert(0, str(current_dir / 'Cnpi_RAG'))

from Cnpi_RAG.nodes.sql_query_info_check import sql_query_info_check_node

# Test case 1: CST Day Shift এর class routine চাইছে কিন্তু semester নেই
state1 = {
    'user_input': 'How can I get the class Routine for the CST Department Day Shift?',
    'normalized_query': 'How can I get the class Routine for the CST Department Day Shift?',
    'sql_query': {}
}

result1 = sql_query_info_check_node(state1)
sql_state1 = result1.get('sql_query', {})

print('Test 1: CST Day Shift class routine (semester missing)')
print(f'short_info: {sql_state1.get("short_info")}')
print(f'missing_shift: {sql_state1.get("missing_shift")}')
print(f'missing_department: {sql_state1.get("missing_department")}')
print(f'missing_semester: {sql_state1.get("missing_semester")}')
print(f'Clarification: {sql_state1.get("final_answer", "N/A")}')
print()

# Test case 2: সব তথ্য আছে
state2 = {
    'user_input': 'CST Day Shift 5th semester er class routine',
    'normalized_query': 'CST Day Shift 5th semester class routine',
    'sql_query': {}
}

result2 = sql_query_info_check_node(state2)
sql_state2 = result2.get('sql_query', {})

print('Test 2: CST Day Shift 5th semester routine (all info present)')
print(f'short_info: {sql_state2.get("short_info")}')
print(f'missing_shift: {sql_state2.get("missing_shift")}')
print(f'missing_department: {sql_state2.get("missing_department")}')
print(f'missing_semester: {sql_state2.get("missing_semester")}')
print()

# Test case 3: শুধু "class routine dao" - সব কিছু missing
state3 = {
    'user_input': 'class routine dao',
    'normalized_query': 'class routine',
    'sql_query': {}
}

result3 = sql_query_info_check_node(state3)
sql_state3 = result3.get('sql_query', {})

print('Test 3: Just "class routine" (all missing)')
print(f'short_info: {sql_state3.get("short_info")}')
print(f'missing_shift: {sql_state3.get("missing_shift")}')
print(f'missing_department: {sql_state3.get("missing_department")}')
print(f'missing_semester: {sql_state3.get("missing_semester")}')
print(f'Clarification: {sql_state3.get("final_answer", "N/A")}')
