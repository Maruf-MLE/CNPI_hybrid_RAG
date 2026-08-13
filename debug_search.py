"""
Debug Vector Search and BM25 Search Issues
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'Cnpi_RAG')
sys.path.insert(0, 'plan')

from utils.embedding_utils import vector_search, bm25_search

print('Testing Vector Search:')
print('=' * 70)
try:
    results = vector_search('test query', table_name='documents', top_k=2)
    print(f'✅ Success! Found {len(results)} results')
    if results:
        content = results[0].get('content', '')[:50]
        print(f'First result: {content}...')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

print('\n\nTesting BM25 Search:')
print('=' * 70)
try:
    results = bm25_search('test query', table_name='documents', top_k=2)
    print(f'✅ Success! Found {len(results)} results')
    if results:
        content = results[0].get('content', '')[:50]
        print(f'First result: {content}...')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

print('\n\nTesting Hybrid Search (Parallel):')
print('=' * 70)
try:
    from utils.embedding_utils import hybrid_search
    import time
    
    start = time.time()
    results = hybrid_search('CST Department', table_name='documents', top_k=3)
    elapsed = time.time() - start
    
    print(f'✅ Success! Found {len(results)} results in {elapsed:.2f}s')
    if results:
        print(f'Top RRF score: {results[0].get("rrf_score", 0):.4f}')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
