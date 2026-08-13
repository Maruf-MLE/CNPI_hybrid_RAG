"""
Test BM25 Search Functionality
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'Cnpi_RAG')
sys.path.insert(0, 'plan')

from utils.db_utils import get_db_connection

print('Testing BM25 Search Directly')
print('=' * 70)

# Test 1: Check if tsvector column has data
print('\n[Test 1] Checking tsvector column data...')
conn = get_db_connection()
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM documents WHERE tsv IS NOT NULL;")
count = cur.fetchone()[0]
print(f'Documents with tsvector: {count}')

if count == 0:
    print('❌ No tsvector data found! Need to generate tsvector.')
else:
    print('✅ Tsvector data exists')

# Test 2: Check sample tsvector
cur.execute("SELECT content, tsv FROM documents WHERE tsv IS NOT NULL LIMIT 1;")
row = cur.fetchone()
if row:
    print(f'\nSample content: {row[0][:80]}...')
    print(f'Sample tsvector: {str(row[1])[:80]}...')

# Test 3: Try direct BM25 query
print('\n[Test 2] Testing direct BM25 SQL query...')
test_query = "CST Department"

# Tokenize
import re
tokens = re.findall(r'[A-Za-z0-9]+', test_query)
tsquery_str = " | ".join(tokens)
print(f'Search tokens: {tokens}')
print(f'TSQuery string: {tsquery_str}')

try:
    sql = """
        SELECT
            content,
            meta AS metadata,
            ts_rank_cd(tsv, to_tsquery('english', %s)) AS rank
        FROM documents
        WHERE tsv @@ to_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT 5;
    """
    
    cur.execute(sql, (tsquery_str, tsquery_str))
    results = cur.fetchall()
    
    print(f'\n✅ BM25 Query Success! Found {len(results)} results')
    
    if results:
        print('\nTop 3 Results:')
        for i, row in enumerate(results[:3], 1):
            content_preview = row[0][:100] if row[0] else ''
            print(f'{i}. Rank: {row[2]:.4f} | Content: {content_preview}...')
    else:
        print('⚠️ Query executed but returned 0 results')
        
        # Check if ANY documents match
        cur.execute("SELECT COUNT(*) FROM documents WHERE tsv @@ to_tsquery('english', %s);", (tsquery_str,))
        match_count = cur.fetchone()[0]
        print(f'Documents matching query: {match_count}')
        
except Exception as e:
    print(f'❌ BM25 Query Failed: {e}')
    import traceback
    traceback.print_exc()

cur.close()
conn.close()

# Test 4: Test via utility function
print('\n[Test 3] Testing via bm25_search() function...')
try:
    from utils.embedding_utils import bm25_search
    
    results = bm25_search('CST Department', table_name='documents', top_k=3)
    print(f'✅ Function call success! Found {len(results)} results')
    
    if results:
        print('\nTop result:')
        print(f"Content: {results[0].get('content', '')[:100]}...")
        print(f"Rank: {results[0].get('rank', 0):.4f}")
    
except Exception as e:
    print(f'❌ Function call failed: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '=' * 70)
print('BM25 Search Test Complete')
