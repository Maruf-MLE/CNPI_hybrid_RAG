"""
Retrieval-Based SQL Query Generator
=====================================

This module uses embedding similarity + BM25 word search to find relevant context
from the documents table, then automatically generates SQL queries.

Instead of rule-based pattern matching, this approach:
1. Embeds the user query
2. Searches documents table using hybrid search (vector + BM25)
3. Analyzes retrieved context to determine query type
4. Automatically generates appropriate SQL query
"""

from typing import Optional, Tuple, Dict, Any, List
import re


class RetrievalBasedSQLGenerator:
    """Generate SQL queries using embedding + BM25 retrieval from documents table."""
    
    def __init__(self):
        """Initialize the retrieval-based SQL generator."""
        pass
    
    def generate(self, query: str) -> Tuple[Optional[str], str, List[Dict[str, Any]]]:
        """
        Generate SQL query using retrieval from documents table.
        
        Args:
            query: Natural language query (already normalized/translated)
            
        Returns:
            Tuple of (sql_query, query_type, retrieved_contexts)
            - sql_query: Generated SQL string or None if out of scope
            - query_type: Type of query detected from context
            - retrieved_contexts: List of relevant contexts found
        """
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from utils.embedding_utils import hybrid_search
        
        # Step 1: Retrieve relevant contexts using hybrid search
        contexts = hybrid_search(
            query_text=query,
            table_name="documents",
            top_k=5
        )
        
        if not contexts or len(contexts) == 0:
            return None, "no_context_found", []
        
        print(f"[RetrievalSQL] Retrieved {len(contexts)} contexts")
        for i, ctx in enumerate(contexts, 1):
            content_preview = str(ctx.get('content', ''))[:100]
            score = ctx.get('rrf_score', 0)
            print(f"  [{i}] Score: {score:.4f} | {content_preview}...")
        
        # Step 2: Analyze contexts to determine query type and extract info
        query_info = self._analyze_contexts(query, contexts)
        
        # Step 3: Generate SQL based on extracted information
        sql_query, query_type = self._generate_sql_from_info(query_info)
        
        return sql_query, query_type, contexts
    
    def _analyze_contexts(self, query: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze retrieved contexts to extract query-relevant information.
        
        Returns a dictionary with extracted info like:
        - query_type: "ci_query", "teacher_list", "person_contact", etc.
        - department: Department code if found
        - shift: Shift info if found
        - person_name: Person name if found
        - doc_types: List of document types in contexts
        """
        query_lower = query.lower()
        
        info = {
            "query_type": "unknown",
            "department": None,
            "shift": None,
            "person_name": None,
            "doc_types": set(),
            "is_count_query": False,
            "is_list_query": False,
        }
        
        # Collect doc_types from metadata
        for ctx in contexts:
            meta = ctx.get('metadata', {})
            if isinstance(meta, dict) and 'doc_type' in meta:
                info['doc_types'].add(meta['doc_type'])
        
        # Determine query type based on keywords and context
        if any(kw in query_lower for kw in ['chief instructor', 'ci', 'চিফ ইন্সট্রাক্টর']):
            info['query_type'] = 'ci_query'
        elif any(kw in query_lower for kw in ['teacher', 'শিক্ষক', 'instructor']) and 'ci' not in query_lower:
            if any(kw in query_lower for kw in ['how many', 'count', 'total', 'কত']):
                info['query_type'] = 'teacher_count'
                info['is_count_query'] = True
            else:
                info['query_type'] = 'teacher_list'
                info['is_list_query'] = True
        elif any(kw in query_lower for kw in ['phone', 'number', 'email', 'contact', 'ফোন']):
            info['query_type'] = 'person_contact'
        elif any(kw in query_lower for kw in ['all department', 'list department', 'departments']):
            info['query_type'] = 'department_list'
        elif any(kw in query_lower for kw in ['total teacher', 'total student', 'total staff']):
            if any(kw in query_lower for kw in ['institution', 'college', 'cnpi', 'polytechnic']):
                info['query_type'] = 'institution_stats'
        
        # Extract department from query or contexts
        info['department'] = self._extract_department(query, contexts)
        
        # Extract shift from query
        info['shift'] = self._extract_shift(query)
        
        # Extract person name from query or contexts
        info['person_name'] = self._extract_person_name(query, contexts)
        
        return info
    
    def _extract_department(self, query: str, contexts: List[Dict[str, Any]]) -> Optional[str]:
        """Extract department code from query or contexts."""
        query_upper = query.upper()
        
        # Department codes with priority order
        dept_codes = ['CST', 'ENT', 'RAC', 'ET', 'FT', 'MT', 'NON-TECH', 'GENERAL']
        
        # Try to find in query first
        for dept in dept_codes:
            if re.search(r'\b' + re.escape(dept) + r'\b', query_upper):
                return dept
        
        # Try to find in contexts metadata
        for ctx in contexts:
            meta = ctx.get('metadata', {})
            if isinstance(meta, dict):
                dept = meta.get('department')
                if dept and dept.upper() in dept_codes:
                    return dept.upper()
        
        return None
    
    def _extract_shift(self, query: str) -> Optional[str]:
        """Extract shift from query."""
        query_lower = query.lower()
        
        shift_map = {
            '1st': '1st', 'first': '1st', 'morning': '1st', 'মর্নিং': '1st', 'প্রথম': '1st',
            '2nd': '2nd', 'second': '2nd', 'day': '2nd', 'ডে': '2nd', 'দ্বিতীয়': '2nd',
        }
        
        for keyword, shift_code in shift_map.items():
            if keyword in query_lower:
                return shift_code
        
        return None
    
    def _extract_person_name(self, query: str, contexts: List[Dict[str, Any]]) -> Optional[str]:
        """Extract person name from query or contexts."""
        # Try from query first
        stop_words = ['what', 'is', 'the', 'phone', 'number', 'of', 'email', 
                     'contact', 'sir', 'madam', 'teacher', 'who', 'which']
        
        cleaned = re.sub(r'[^\w\s.]', ' ', query)
        words = cleaned.split()
        
        name_words = []
        for word in words:
            if word.lower() in stop_words or len(word) < 2:
                continue
            if word and (word[0].isupper() or '.' in word):
                name_words.append(word)
        
        if name_words:
            return ' '.join(name_words)
        
        # Try from contexts metadata
        for ctx in contexts:
            meta = ctx.get('metadata', {})
            if isinstance(meta, dict):
                name = meta.get('name')
                if name:
                    return name
        
        return None
    
    def _generate_sql_from_info(self, info: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Generate SQL query from extracted information."""
        query_type = info['query_type']
        
        if query_type == 'ci_query':
            return self._generate_ci_sql(info)
        elif query_type == 'teacher_count':
            return self._generate_teacher_count_sql(info)
        elif query_type == 'teacher_list':
            return self._generate_teacher_list_sql(info)
        elif query_type == 'person_contact':
            return self._generate_person_contact_sql(info)
        elif query_type == 'department_list':
            return self._generate_department_list_sql()
        elif query_type == 'institution_stats':
            return self._generate_institution_stats_sql()
        else:
            return None, 'unknown_query_type'
    
    def _generate_ci_sql(self, info: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Generate SQL for Chief Instructor query."""
        dept = info.get('department')
        if not dept:
            return None, 'ci_no_dept'
        
        shift = info.get('shift')
        
        sql = f"""SELECT p.name_en, p.name_bn, p.phone_primary, p.phone_secondary
FROM people p
JOIN departments d ON p.department_id = d.department_id
WHERE UPPER(d.short_code) = '{dept}' AND p.is_chief_instructor = TRUE"""
        
        if shift:
            sql += f" AND p.shift = '{shift}'"
        
        sql += ";"
        
        return sql, 'ci_query'
    
    def _generate_teacher_count_sql(self, info: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Generate SQL for teacher count query."""
        dept = info.get('department')
        if not dept:
            return None, 'teacher_count_no_dept'
        
        sql = f"""SELECT COUNT(*) AS total
FROM people p
JOIN departments d ON p.department_id = d.department_id
JOIN designations des ON p.designation_id = des.designation_id
WHERE UPPER(d.short_code) = '{dept}' 
  AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');"""
        
        return sql, 'teacher_count'
    
    def _generate_teacher_list_sql(self, info: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Generate SQL for teacher list query."""
        dept = info.get('department')
        if not dept:
            return None, 'teacher_list_no_dept'
        
        sql = f"""SELECT p.name_en, p.name_bn, des.title_en, des.title_bn
FROM people p
JOIN departments d ON p.department_id = d.department_id
LEFT JOIN designations des ON p.designation_id = des.designation_id
WHERE UPPER(d.short_code) = '{dept}' 
  AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');"""
        
        return sql, 'teacher_list'
    
    def _generate_person_contact_sql(self, info: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Generate SQL for person contact query."""
        name = info.get('person_name')
        if not name:
            return None, 'person_contact_no_name'
        
        sql = f"""SELECT p.name_en, p.name_bn, d.name_en AS department, 
       des.title_en AS designation, p.phone_primary, 
       p.phone_secondary, p.email
FROM people p
LEFT JOIN departments d ON p.department_id = d.department_id
LEFT JOIN designations des ON p.designation_id = des.designation_id
WHERE p.name_en %% '{name}'
ORDER BY similarity(p.name_en, '{name}') DESC
LIMIT 5;"""
        
        return sql, 'person_contact'
    
    def _generate_department_list_sql(self) -> Tuple[Optional[str], str]:
        """Generate SQL for department list query."""
        sql = """SELECT name_en, name_bn, short_code, shift_info, 
       total_teachers, total_labs
FROM departments
ORDER BY short_code;"""
        
        return sql, 'department_list'
    
    def _generate_institution_stats_sql(self) -> Tuple[Optional[str], str]:
        """Generate SQL for institution statistics."""
        sql = """SELECT total_teachers, total_students, total_staff, 
       total_workforce, total_departments, total_labs
FROM institutions WHERE short_name = 'CNPI';"""
        
        return sql, 'institution_stats'


# =============================================================================
# Module-level function for easy import
# =============================================================================

_generator = RetrievalBasedSQLGenerator()

def generate_sql_from_retrieval(query: str) -> Tuple[Optional[str], str, List[Dict[str, Any]]]:
    """
    Generate SQL query using embedding + BM25 retrieval.
    
    Args:
        query: Natural language query (already normalized/translated)
        
    Returns:
        Tuple of (sql_query, query_type, retrieved_contexts)
    """
    return _generator.generate(query)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    test_cases = [
        "Who is the Chief Instructor of the CST 2nd shift?",
        "List all teachers in CST department",
        "How many teachers are in CST?",
        "What is the phone number of Rejuanul Arefin?",
    ]
    
    print("=" * 80)
    print("Testing Retrieval-Based SQL Query Generator")
    print("=" * 80)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n{i}. Query: {query}")
        try:
            sql, query_type, contexts = generate_sql_from_retrieval(query)
            print(f"   Type: {query_type}")
            print(f"   Contexts found: {len(contexts)}")
            if sql:
                print(f"   SQL:\n{sql}")
            else:
                print(f"   Result: Could not generate SQL")
        except Exception as e:
            print(f"   ERROR: {e}")
