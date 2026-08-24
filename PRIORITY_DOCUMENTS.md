# Priority Documents - সবসময় Retrieve হওয়া Documents

## সংক্ষিপ্ত বিবরণ

এই feature টি RAG system এ এমন documents add করার সুবিধা দেয় যেগুলো **সবসময় automatically** retrieve হবে, যেকোনো query এর জন্য।

### কিভাবে কাজ করে:

1. **Priority Documents Table**: একটি নতুন table (`priority_documents`) তৈরি করা হয়েছে যেখানে priority documents এর reference থাকে
2. **Always Retrieve**: এই documents গুলো প্রতিটি query তে automatically include হয়
3. **Dynamic Retrieval**: 
   - যদি `top_k=10` এবং `3` টা priority docs থাকে
   - তাহলে: `3` (priority) + `7` (query-based) = `10` total documents
4. **Priority Order**: Priority docs সবসময় প্রথমে আসে, তারপর query-based results

---

## Database Schema

### Priority Documents Table

```sql
CREATE TABLE priority_documents (
    priority_id SERIAL PRIMARY KEY,
    doc_id INTEGER REFERENCES documents(doc_id) ON DELETE CASCADE,
    priority_order INTEGER DEFAULT 0,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(doc_id)
);

CREATE INDEX idx_priority_docs_active ON priority_documents(is_active, priority_order);
```

---

## API Endpoints

### 1. List Priority Documents
```http
GET /admin-panel/api/priority-docs/?active_only=true
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "priority_documents": [
    {
      "priority_id": 1,
      "doc_id": 123,
      "priority_order": 0,
      "reason": "Important context about CST department",
      "chunk_id": "doc_001_chunk_01",
      "content": "কম্পিউটার বিজ্ঞান ও প্রযুক্তি বিভাগ...",
      "doc_type": "department_info",
      "is_active": true
    }
  ]
}
```

---

### 2. Add Priority Document
```http
POST /admin-panel/api/priority-docs/add/
Content-Type: application/json

{
  "doc_id": 123,
  "priority_order": 0,
  "reason": "Important context for all queries"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Document added to priority list successfully",
  "priority_document": {
    "priority_id": 1,
    "doc_id": 123,
    "priority_order": 0,
    "reason": "Important context for all queries",
    "created_at": "2026-08-23T14:30:00Z",
    "is_active": true
  }
}
```

---

### 3. Remove Priority Document
```http
POST /admin-panel/api/priority-docs/remove/
Content-Type: application/json

{
  "priority_id": 1
}
```
অথবা
```json
{
  "doc_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "message": "Priority document removed successfully"
}
```

---

### 4. Update Priority Order
```http
POST /admin-panel/api/priority-docs/update-order/
Content-Type: application/json

{
  "priority_id": 1,
  "priority_order": 5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Priority order updated successfully",
  "priority_document": {
    "priority_id": 1,
    "doc_id": 123,
    "priority_order": 5,
    ...
  }
}
```

---

### 5. Get Statistics
```http
GET /admin-panel/api/priority-docs/stats/
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_active": 5,
    "by_type": [
      {"doc_type": "department_info", "count": 2},
      {"doc_type": "general_info", "count": 3}
    ]
  }
}
```

---

## Retrieval Logic

### Admin Panel Search (semantic_search)

**File:** `cnpi_api/admin_panel/services.py`

```python
def semantic_search(query: str, top_k: int = 5, include_priority: bool = True):
    """
    Priority docs সবসময় প্রথমে আসে, তারপর query-based results
    
    Example: top_k=10, 3 priority docs
    → 3 priority + 7 query-based = 10 total
    """
```

### RAG Hybrid Search (hybrid_search)

**File:** `Cnpi_RAG/utils/embedding_utils.py`

```python
def hybrid_search(query_text: str, top_k: int = 5, include_priority: bool = True):
    """
    Combines:
    1. Priority documents (always included)
    2. Vector search (pgvector cosine similarity)
    3. BM25 search (full-text search)
    
    Using Weighted RRF (Reciprocal Rank Fusion)
    """
```

---

## Usage Example

### Python

```python
import requests

# 1. Search for a document
response = requests.post("http://localhost:8000/admin-panel/api/search/", json={
    "query": "কম্পিউটার বিজ্ঞান বিভাগ",
    "top_k": 5
})
doc_id = response.json()["results"][0]["doc_id"]

# 2. Add to priority list
requests.post("http://localhost:8000/admin-panel/api/priority-docs/add/", json={
    "doc_id": doc_id,
    "priority_order": 0,
    "reason": "Important department information"
})

# 3. Test retrieval
response = requests.post("http://localhost:8000/api/chat/", json={
    "query": "শিক্ষকদের তালিকা দেখাও",
    "session_id": "test_001"
})
# Priority doc সবসময় context এ থাকবে

# 4. Remove from priority list
requests.post("http://localhost:8000/admin-panel/api/priority-docs/remove/", json={
    "doc_id": doc_id
})
```

---

## Test করার জন্য

### Test Script চালানো

```bash
python test_priority_docs.py
```

এই script:
- ✓ Priority docs add করবে
- ✓ List করবে
- ✓ Update করবে
- ✓ Retrieval test করবে
- ✓ Remove করবে (cleanup)

---

## Use Cases

### 1. Institute Information
প্রতিষ্ঠানের basic information সবসময় available রাখা:
```
- প্রতিষ্ঠানের নাম, ঠিকানা
- যোগাযোগের তথ্য
- প্রতিষ্ঠানের ইতিহাস
```

### 2. Important Policies
গুরুত্বপূর্ণ নীতিমালা:
```
- ভর্তি নীতিমালা
- পরীক্ষার নিয়মাবলী
- ছুটির নিয়ম
```

### 3. FAQ Answers
সবচেয়ে common questions এর answers:
```
- "প্রতিষ্ঠান কোথায়?"
- "ভর্তি কিভাবে হয়?"
- "কোন কোন বিভাগ আছে?"
```

### 4. Emergency Contact
জরুরি যোগাযোগের তথ্য:
```
- প্রধান শিক্ষকের নম্বর
- অফিসের নম্বর
- জরুরি হটলাইন
```

---

## Performance Considerations

### Retrieval Time
- Priority docs খুব দ্রুত retrieve হয় (indexed query)
- Query-based search parallel এ চলে (vector + BM25)
- Overall latency: +5-10ms (priority docs এর জন্য)

### Database Impact
- Minimal overhead (simple JOIN query)
- Indexed by `is_active` and `priority_order`
- No performance degradation with 10-50 priority docs

### Memory Impact
- Priority docs memory তে cache করা হয় না (always fresh from DB)
- Each query: 1 extra DB call (cached by connection pool)

---

## Best Practices

### 1. কত priority docs রাখা উচিত?
- **Recommended**: 5-10 documents
- **Maximum**: 20 documents
- বেশি হলে retrieval quality কমে যাবে

### 2. কোন documents priority তে রাখা উচিত?
✓ Institute basic info  
✓ Common FAQs  
✓ Important policies  
✓ Emergency contacts  
✗ Specific teacher info (query-based retrieval better)  
✗ Routine/schedule (time-sensitive)  

### 3. Priority Order কিভাবে set করবো?
- `0` = সবচেয়ে important (প্রথমে আসবে)
- `1-5` = Important
- `6-10` = Moderately important
- `10+` = Less important

### 4. কখন remove করবো?
- Outdated information হলে
- Query-based retrieval better results দিলে
- Content duplicate হলে

---

## Monitoring

### Check Priority Docs Count
```bash
curl http://localhost:8000/admin-panel/api/priority-docs/stats/
```

### Check Retrieval Performance
```bash
# Enable debug logging
export DEBUG=true

# Check logs for:
# "[hybrid_search] Retrieved N priority documents"
# "[hybrid_search] Returning X priority + Y query-based = Z total docs"
```

---

## Migration & Rollback

### Migration Applied
```bash
cd cnpi_api
python manage.py migrate
```

### Rollback (if needed)
```sql
DROP TABLE IF EXISTS priority_documents;
```

তারপর code revert করুন:
```bash
git revert <commit_hash>
```

---

## Future Enhancements

### Planned Features
1. ✓ Admin Panel UI for easier management
2. ⏳ Automatic expiration (temporal_analysis integration)
3. ⏳ Context-aware priority (department-specific)
4. ⏳ A/B testing framework
5. ⏳ Analytics dashboard

### Not Planned
- ✗ User-level priority docs (too complex)
- ✗ Dynamic priority based on query (performance issues)

---

## Troubleshooting

### Priority docs not showing in results?
1. Check `is_active = TRUE` in database
2. Check `include_priority=True` in search calls
3. Verify DB migration applied successfully

### Duplicate documents in results?
- Priority docs are excluded from query-based search automatically
- Check deduplication logic in `hybrid_search()`

### Slow retrieval?
- Check if priority_documents table is indexed
- Reduce priority docs count (<20 recommended)
- Monitor DB connection pool

---

## Support

এই feature সম্পর্কে কোনো প্রশ্ন থাকলে:
1. Check logs: `logs/rag_system.log`
2. Run test script: `python test_priority_docs.py`
3. Check DB: `SELECT * FROM priority_documents WHERE is_active = TRUE;`

---

**Version**: 1.0  
**Last Updated**: 2026-08-23  
**Author**: CNPI RAG System Team
