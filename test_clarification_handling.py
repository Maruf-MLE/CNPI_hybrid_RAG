import sys
from pathlib import Path

current_dir = Path.cwd()
sys.path.insert(0, str(current_dir / 'plan'))
sys.path.insert(0, str(current_dir / 'Cnpi_RAG'))

from Cnpi_RAG.nodes.hybrid_append_sub_answer import append_sub_answer_node

# Test Case 1: Sub-query যেখানে context পাওয়া গেছে (normal case)
print("=" * 70)
print("Test 1: Normal sub-query with context")
print("=" * 70)

state1 = {
    "user_input": "CST Day Shift এর CI কে?",
    "parent_sub_query": "CST Day Shift এর CI কে?",
    "is_sub_query_call": True,
    "decided_path": "sql_retrieve",
    "final_answer": "",
    "answer_status": "found",
    "sql_retrieve": {
        "context_with_meta": "Name: Md. Jewel Rana, Position: Chief Instructor, Dept: CST, Shift: Day",
        "context_found": True,
    },
    "hybrid": {
        "depth": 1,
        "total_sub_q": 2,
        "sub_query_list": [],
        "sub_query_ans": [],
        "sub_ans_count": 0,
        "merge_retries": 0,
    },
}

result1 = append_sub_answer_node(state1)
ans1 = result1["hybrid"]["sub_query_ans"][0]
print(f"Query: {ans1['query']}")
print(f"Context: {ans1['context'][:80] if ans1['context'] else 'None'}...")
print(f"Final Answer: {ans1['final_answer'][:80]}...")
print(f"Source Path: {ans1['source_path']}")
print()

# Test Case 2: Sub-query যেখানে need_more_info (shift missing)
print("=" * 70)
print("Test 2: Sub-query with need_more_info (shift missing)")
print("=" * 70)

state2 = {
    "user_input": "CST department এর CI কে?",
    "parent_sub_query": "CST department এর CI কে?",
    "is_sub_query_call": True,
    "decided_path": "sql_query",
    "final_answer": "দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?",
    "answer_status": "need_more_info",
    "sql_query": {
        "short_info": True,
        "final_answer": "দয়া করে বলুন, আপনি কোন Shift-এর তথ্য জানতে চাচ্ছেন? 1st/Morning নাকি 2nd/Day Shift?",
        "missing_shift": True,
        "missing_department": False,
        "missing_semester": False,
    },
    "hybrid": {
        "depth": 1,
        "total_sub_q": 2,
        "sub_query_list": [],
        "sub_query_ans": [],
        "sub_ans_count": 0,
        "merge_retries": 0,
    },
}

result2 = append_sub_answer_node(state2)
ans2 = result2["hybrid"]["sub_query_ans"][0]
print(f"Query: {ans2['query']}")
print(f"Context: {ans2['context']}")
print(f"Final Answer: {ans2['final_answer']}")
print(f"Source Path: {ans2['source_path']}")
print()

# Test Case 3: Sub-query যেখানে semester missing (class routine)
print("=" * 70)
print("Test 3: Sub-query with semester missing (class routine)")
print("=" * 70)

state3 = {
    "user_input": "CST Day Shift এর class routine",
    "parent_sub_query": "CST Day Shift এর class routine",
    "is_sub_query_call": True,
    "decided_path": "sql_query",
    "final_answer": "অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Routine চাচ্ছেন? (1st থেকে 8th পর্যন্ত)",
    "answer_status": "need_more_info",
    "sql_query": {
        "short_info": True,
        "final_answer": "অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Routine চাচ্ছেন? (1st থেকে 8th পর্যন্ত)",
        "missing_shift": False,
        "missing_department": False,
        "missing_semester": True,
    },
    "hybrid": {
        "depth": 1,
        "total_sub_q": 3,
        "sub_query_list": [],
        "sub_query_ans": [],
        "sub_ans_count": 0,
        "merge_retries": 0,
    },
}

result3 = append_sub_answer_node(state3)
ans3 = result3["hybrid"]["sub_query_ans"][0]
print(f"Query: {ans3['query']}")
print(f"Context: {ans3['context']}")
print(f"Final Answer: {ans3['final_answer']}")
print(f"Source Path: {ans3['source_path']}")
print()

# Test Case 4: Mixed scenario - একটা sub-query তে context আছে, আরেকটায় need_more_info
print("=" * 70)
print("Test 4: Simulating merge with mixed results")
print("=" * 70)

# এখানে আমরা দেখাচ্ছি merge_sub_answers node কী পাবে
sub_answers = [
    {
        "query": "CST Day Shift 5th semester এর CI কে?",
        "context": "Name: Md. Jewel Rana, Position: Chief Instructor",
        "final_answer": "Name: Md. Jewel Rana, Position: Chief Instructor",
        "source_path": "sql_retrieve",
    },
    {
        "query": "CST Day Shift এর class routine",
        "context": None,
        "final_answer": "অনুগ্রহ করে বলুন, আপনি কোন Semester-এর Class Routine চাচ্ছেন? (1st থেকে 8th পর্যন্ত)",
        "source_path": "sql_query",
    },
]

print("Sub-answers যা merge node এ যাবে:")
for i, sa in enumerate(sub_answers, 1):
    print(f"\n[Sub-Answer {i}]")
    print(f"  Query: {sa['query']}")
    print(f"  Context: {sa['context']}")
    print(f"  Answer: {sa['final_answer']}")
    print(f"  Source: {sa['source_path']}")

print("\n" + "=" * 70)
print("✅ Merge node এখন বুঝতে পারবে যে 2nd sub-query তে clarification দরকার!")
print("=" * 70)
