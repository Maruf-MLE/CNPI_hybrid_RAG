# Database Security Implementation

## Overview

এই RAG সিস্টেমে **দুই-স্তরের database security** implement করা হয়েছে যাতে:
- ✅ RAG system শুধুমাত্র **READ-ONLY** access পায়
- ✅ Admin Panel **WRITE** access পায় (INSERT, UPDATE, DELETE)

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Database Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────┐          ┌────────────────────┐    │
│  │   RAG System       │          │   Admin Panel      │    │
│  │  (Cnpi_RAG/)       │          │  (cnpi_api/)       │    │
│  └────────┬───────────┘          └─────────┬──────────┘    │
│           │                                 │                │
│           │ allow_write=False               │ allow_write=True │
│           ▼                                 ▼                │
│  ┌────────────────────────────────────────────────────┐    │
│  │         execute_query() Security Layer             │    │
│  │  • Validates SQL queries                           │    │
│  │  • Blocks: INSERT, UPDATE, DELETE, DROP, etc.     │    │
│  │  • Allows: SELECT only (if allow_write=False)     │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│                  PostgreSQL Database                         │
│              (notices, documents, etc.)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Core Security Function (`Cnpi_RAG/utils/db_utils.py`)

#### `is_read_only_query(query: str)`
SQL query validate করে এবং শুধুমাত্র SELECT query allow করে।

**Blocked Keywords:**
- `INSERT`, `UPDATE`, `DELETE`
- `DROP`, `CREATE`, `ALTER`, `TRUNCATE`
- `GRANT`, `REVOKE`
- `EXEC`, `EXECUTE`, `CALL`
- `SET`, `DECLARE`

**Security Features:**
- ✅ SQL comments remove করে (single-line `--` এবং multi-line `/* */`)
- ✅ Multiple statements block করে (SQL injection protection)
- ✅ Case-insensitive keyword matching
- ✅ Whole-word matching (false positives avoid করে)

#### `get_db_connection(allow_write: bool = False)`
Database connection return করে।
- Default: `allow_write=False` (read-only)
- Admin panel: `allow_write=True` (full access)

#### `execute_query(query, params, fetch, allow_write: bool = False)`
SQL query execute করে security check সহ।

**Parameters:**
- `query`: SQL query string
- `params`: Parameterized query values (SQL injection protection)
- `fetch`: `True` for SELECT, `False` for write operations
- `allow_write`: `True` to bypass read-only restrictions

---

## Usage Examples

### ✅ RAG System (Read-Only)

```python
# Cnpi_RAG/nodes/sql_query_create.py
from utils.db_utils import execute_query

# ✅ SELECT query - ALLOWED
results = execute_query(
    "SELECT notice_id, title_bn, content_bn FROM notices WHERE institution_id = 1",
    fetch=True
)

# ❌ DELETE query - BLOCKED
results = execute_query(
    "DELETE FROM notices WHERE notice_id = 1",
    fetch=False
)
# Raises: PermissionError: Security violation: Write operation 'DELETE' not allowed
```

### ✅ Admin Panel (Full Access)

```python
# cnpi_api/admin_panel/services.py
from utils.db_utils import get_db_connection

# Admin panel needs write access
conn = get_db_connection(allow_write=True)

# ✅ INSERT query - ALLOWED (because allow_write=True)
cursor.execute("""
    INSERT INTO notices (institution_id, title_bn, content_bn) 
    VALUES (%s, %s, %s)
""", (1, "নতুন নোটিশ", "বিস্তারিত..."))
conn.commit()
```

---

## Security Testing

### Test 1: RAG System Read-Only Enforcement

```python
# Test file: test_rag_security.py
from Cnpi_RAG.utils.db_utils import execute_query

# Should work
result = execute_query("SELECT * FROM notices LIMIT 1", fetch=True)
print("✅ SELECT allowed:", len(result))

# Should fail
try:
    execute_query("DELETE FROM notices WHERE notice_id = 999", fetch=False)
    print("❌ Security breach!")
except PermissionError as e:
    print("✅ DELETE blocked:", e)
```

### Test 2: Admin Panel Write Access

```python
# Test file: test_admin_security.py
from cnpi_api.admin_panel.services import create_document

# Should work - creates new document
result = create_document(
    chunk_id="test_security_001",
    content="This is a test document for security validation",
    doc_type="general"
)
print("✅ INSERT allowed:", result)
```

---

## File Modifications

### Modified Files:
1. **`Cnpi_RAG/utils/db_utils.py`**
   - Added `is_read_only_query()` function
   - Updated `get_db_connection()` with `allow_write` parameter
   - Updated `execute_query()` with security checks

2. **`cnpi_api/admin_panel/services.py`**
   - Updated `_get_conn()` to use `allow_write=True`

### Deleted Files:
- `Cnpi_RAG/utils/db_utils_admin.py` (no longer needed)

---

## Protected Operations

### RAG System (READ-ONLY)
| File | Function | Query Type | Status |
|------|----------|------------|--------|
| `sql_query_create.py` | `sql_query_create_node()` | SELECT | ✅ Allowed |
| `sql_query_db_call.py` | `sql_query_db_call_node()` | SELECT | ✅ Allowed |
| `retrieve.py` | `retrieve()` | SELECT | ✅ Allowed |

### Admin Panel (FULL ACCESS)
| File | Function | Query Type | Status |
|------|----------|------------|--------|
| `services.py` | `create_document()` | INSERT | ✅ Allowed |
| `services.py` | `update_document()` | UPDATE | ✅ Allowed |
| `services.py` | `semantic_search()` | SELECT | ✅ Allowed |
| `services.py` | Insert into notices | INSERT | ✅ Allowed |

---

## Security Best Practices

### ✅ DO:
- RAG queries-এ শুধুমাত্র `execute_query()` ব্যবহার করুন (default read-only)
- Admin panel-এ `allow_write=True` সহ connection নিন
- Parameterized queries ব্যবহার করুন SQL injection avoid করতে
- Production-এ database logs monitor করুন

### ❌ DON'T:
- RAG code-এ কখনো `allow_write=True` ব্যবহার করবেন না
- Raw SQL string concatenation করবেন না
- User input directly query-তে pass করবেন না
- Security validation bypass করার চেষ্টা করবেন না

---

## Additional Security Measures

### Database-Level Protection (Optional)

আরো strong security-র জন্য, PostgreSQL-এ দুটি আলাদা user তৈরি করতে পারেন:

```sql
-- Read-only user for RAG system
CREATE USER rag_readonly WITH PASSWORD 'secure_password_here';
GRANT CONNECT ON DATABASE college TO rag_readonly;
GRANT USAGE ON SCHEMA public TO rag_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO rag_readonly;

-- Full access user for admin panel
CREATE USER admin_fullaccess WITH PASSWORD 'another_secure_password';
GRANT ALL PRIVILEGES ON DATABASE college TO admin_fullaccess;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_fullaccess;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin_fullaccess;
```

তারপর `.env` file-এ:
```env
# RAG system connection
RAG_DATABASE_URL=postgresql://rag_readonly:password@host/college

# Admin panel connection
ADMIN_DATABASE_URL=postgresql://admin_fullaccess:password@host/college
```

---

## Monitoring & Logging

Security logs automatically print হয় যখন blocked query attempt হয়:

```
[SECURITY] Query blocked: Write operation 'DELETE' not allowed. Only SELECT queries are permitted.
[SECURITY] Attempted query: DELETE FROM notices WHERE notice_id = 123...
```

Production environment-এ এই logs monitor করুন suspicious activity detect করতে।

---

## Troubleshooting

### Issue: Admin panel INSERT failing
**Solution:** Ensure `services.py` uses `get_db_connection(allow_write=True)`

### Issue: RAG SELECT queries failing
**Solution:** Check query syntax - ensure it's a valid SELECT statement

### Issue: "Multiple statements not allowed" error
**Solution:** Remove semicolons from middle of query (security feature against SQL injection)

---

## Summary

✅ **RAG System**: Read-only access - কোনো data modify করতে পারবে না  
✅ **Admin Panel**: Full access - INSERT/UPDATE/DELETE করতে পারবে  
✅ **Security**: SQL injection protection, keyword validation, query sanitization  
✅ **Flexible**: Application-level control সহ optional database-level protection

এই implementation আপনার RAG system-কে secure রাখবে যাতে শুধুমাত্র authorized admin operations-ই database modify করতে পারে।
