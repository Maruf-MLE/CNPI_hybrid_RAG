"""
Rule-Based SQL Query Generator
================================

This module generates SQL queries using pattern matching instead of LLM calls.
It's faster, more reliable, and cost-free.

Query patterns:
1. Chief Instructor queries (CI)
2. Teacher list/count queries
3. Person phone/contact queries
4. Department list queries
5. Institution statistics
"""

import re
from typing import Optional, Dict, List, Tuple


class SQLQueryGenerator:
    """Rule-based SQL query generator for CNPI database."""
    
    # Department codes
    VALID_DEPTS = {'CST', 'ET', 'ENT', 'RAC', 'FT', 'MT', 'NON-TECH', 'GENERAL'}
    
    # Shift mapping
    SHIFT_MAP = {
        '1st': '1st',
        'first': '1st',
        'morning': '1st',
        'মর্নিং': '1st',
        'প্রথম': '1st',
        '2nd': '2nd',
        'second': '2nd',
        'day': '2nd',
        'ডে': '2nd',
        'দ্বিতীয়': '2nd',
    }
    
    def __init__(self):
        """Initialize the SQL query generator."""
        pass
    
    def generate(self, query: str) -> Tuple[Optional[str], str]:
        """
        Generate SQL query from natural language.
        
        Args:
            query: Natural language query (already normalized/translated)
            
        Returns:
            Tuple of (sql_query, query_type)
            - sql_query: Generated SQL string or None if out of scope
            - query_type: Type of query detected
        """
        # Keep original query for name extraction (needs capital letters)
        query_original = query.strip()
        query_lower = query.lower().strip()
        
        # 1. Check for institution statistics FIRST (before department-specific queries)
        if self._is_institution_stats_query(query_lower):
            return self._generate_institution_stats_query(query_lower)
        
        # 2. Check for Chief Instructor queries
        if self._is_ci_query(query_lower):
            return self._generate_ci_query(query_lower)
        
        # 3. Check for teacher list/count queries
        if self._is_teacher_query(query_lower):
            return self._generate_teacher_query(query_lower)
        
        # 4. Check for person contact queries (use original query for name extraction)
        if self._is_person_query(query_lower):
            return self._generate_person_query(query_original)
        
        # 5. Check for department list query
        if self._is_department_list_query(query_lower):
            return self._generate_department_list_query()
        
        # Out of scope - should go to retrieval path
        return None, "out_of_scope"
    
    # =========================================================================
    # Detection Methods
    # =========================================================================
    
    def _is_ci_query(self, query: str) -> bool:
        """Check if query is asking about Chief Instructor."""
        ci_keywords = ['chief instructor', 'ci', 'চিফ ইন্সট্রাক্টর']
        return any(kw in query for kw in ci_keywords)
    
    def _is_teacher_query(self, query: str) -> bool:
        """Check if query is asking about teachers (list or count)."""
        teacher_keywords = ['teacher', 'শিক্ষক', 'instructor']
        # Exclude CI queries
        if self._is_ci_query(query):
            return False
        return any(kw in query for kw in teacher_keywords)
    
    def _is_person_query(self, query: str) -> bool:
        """Check if query is asking about a specific person's contact."""
        contact_keywords = ['phone', 'number', 'email', 'contact', 'ফোন', 'নাম্বার']
        # Must have a contact keyword and likely a name
        return any(kw in query for kw in contact_keywords)
    
    def _is_department_list_query(self, query: str) -> bool:
        """Check if query is asking for all departments."""
        list_keywords = ['all department', 'list department', 'department list', 
                         'departments', 'সব বিভাগ', 'বিভাগ গুলো']
        return any(kw in query for kw in list_keywords)
    
    def _is_institution_stats_query(self, query: str) -> bool:
        """Check if query is asking for institution-wide statistics."""
        stat_keywords = ['total teacher', 'total student', 'total staff', 
                        'how many', 'মোট শিক্ষক', 'মোট শিক্ষার্থী']
        institution_keywords = ['institution', 'college', 'cnpi', 'polytechnic', 
                               'প্রতিষ্ঠান', 'কলেজ', 'whole', 'entire', 'overall']
        
        # Check if asking about total teachers without specific department
        has_stat = any(sk in query for sk in stat_keywords)
        has_institution = any(ik in query for ik in institution_keywords)
        no_specific_dept = self._extract_department(query) is None
        
        return has_stat and (has_institution or no_specific_dept)
    
    # =========================================================================
    # SQL Generation Methods
    # =========================================================================
    
    def _generate_ci_query(self, query: str) -> Tuple[Optional[str], str]:
        """Generate SQL for Chief Instructor query."""
        # Extract department
        dept = self._extract_department(query)
        if not dept:
            return None, "ci_no_dept"
        
        # Extract shift
        shift = self._extract_shift(query)
        
        # Build SQL
        sql = f"""SELECT p.name_en, p.name_bn, p.phone_primary, p.phone_secondary
FROM people p
JOIN departments d ON p.department_id = d.department_id
WHERE UPPER(d.short_code) = '{dept.upper()}' AND p.is_chief_instructor = TRUE"""
        
        if shift:
            sql += f" AND p.shift = '{shift}'"
        
        sql += ";"
        
        return sql, "ci_query"
    
    def _generate_teacher_query(self, query: str) -> Tuple[Optional[str], str]:
        """Generate SQL for teacher list/count query."""
        # Extract department
        dept = self._extract_department(query)
        if not dept:
            return None, "teacher_no_dept"
        
        # Check if it's a count query
        is_count = any(kw in query for kw in ['how many', 'count', 'total', 'কত', 'সংখ্যা'])
        
        if is_count:
            # Count query
            sql = f"""SELECT COUNT(*) AS total
FROM people p
JOIN departments d ON p.department_id = d.department_id
JOIN designations des ON p.designation_id = des.designation_id
WHERE UPPER(d.short_code) = '{dept.upper()}' 
  AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');"""
        else:
            # List query
            sql = f"""SELECT p.name_en, p.name_bn, des.title_en, des.title_bn
FROM people p
JOIN departments d ON p.department_id = d.department_id
LEFT JOIN designations des ON p.designation_id = des.designation_id
WHERE UPPER(d.short_code) = '{dept.upper()}' 
  AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');"""
        
        return sql, "teacher_query"
    
    def _generate_person_query(self, query: str) -> Tuple[Optional[str], str]:
        """Generate SQL for person contact query."""
        # Extract person name (use original query, not lowercased, for capital detection)
        # But we receive lowercased query, so we need to handle it
        name = self._extract_person_name(query)
        if not name:
            # If no name extracted, query might still be valid but we return a generic search
            # In this case, return None to indicate we need more info
            return None, "person_no_name"
        
        # Use fuzzy search with trigram similarity
        sql = f"""SELECT p.name_en, p.name_bn, d.name_en AS department, 
       des.title_en AS designation, p.phone_primary, 
       p.phone_secondary, p.email
FROM people p
LEFT JOIN departments d ON p.department_id = d.department_id
LEFT JOIN designations des ON p.designation_id = des.designation_id
WHERE p.name_en %% '{name}'
ORDER BY similarity(p.name_en, '{name}') DESC
LIMIT 5;"""
        
        return sql, "person_query"
    
    def _generate_department_list_query(self) -> Tuple[Optional[str], str]:
        """Generate SQL for department list query."""
        sql = """SELECT name_en, name_bn, short_code, shift_info, 
       total_teachers, total_labs
FROM departments
ORDER BY short_code;"""
        
        return sql, "dept_list_query"
    
    def _generate_institution_stats_query(self, query: str) -> Tuple[Optional[str], str]:
        """Generate SQL for institution statistics query."""
        # Determine what statistic is needed
        if 'teacher' in query or 'শিক্ষক' in query:
            sql = "SELECT total_teachers FROM institutions WHERE short_name = 'CNPI';"
        elif 'student' in query or 'শিক্ষার্থী' in query:
            sql = "SELECT total_students FROM institutions WHERE short_name = 'CNPI';"
        elif 'staff' in query or 'কর্মী' in query:
            sql = "SELECT total_staff FROM institutions WHERE short_name = 'CNPI';"
        elif 'workforce' in query:
            sql = "SELECT total_workforce FROM institutions WHERE short_name = 'CNPI';"
        elif 'department' in query or 'বিভাগ' in query:
            sql = "SELECT total_departments FROM institutions WHERE short_name = 'CNPI';"
        else:
            # Return all stats
            sql = """SELECT total_teachers, total_students, total_staff, 
       total_workforce, total_departments, total_labs
FROM institutions WHERE short_name = 'CNPI';"""
        
        return sql, "institution_stats"
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _extract_department(self, query: str) -> Optional[str]:
        """Extract department code from query."""
        query_upper = query.upper()
        
        # Check for department codes with word boundaries to avoid false matches
        # Priority order: longer codes first to avoid substring matches
        dept_priority = ['NON-TECH', 'GENERAL', 'CST', 'ENT', 'RAC', 'ET', 'FT', 'MT']
        
        for dept in dept_priority:
            # Use word boundary check
            import re
            pattern = r'\b' + re.escape(dept) + r'\b'
            if re.search(pattern, query_upper):
                return dept
        
        # Check for full names
        dept_names = {
            'COMPUTER SCIENCE': 'CST',
            'ELECTRICAL TECHNOLOGY': 'ET',
            'ELECTRONICS': 'ENT',
            'REFRIGERATION': 'RAC',
            'FOOD TECHNOLOGY': 'FT',
            'MECHANICAL': 'MT',
        }
        
        for name, code in dept_names.items():
            if name in query_upper:
                return code
        
        return None
    
    def _extract_shift(self, query: str) -> Optional[str]:
        """Extract shift from query."""
        query_lower = query.lower()
        
        for keyword, shift_code in self.SHIFT_MAP.items():
            if keyword in query_lower:
                return shift_code
        
        return None
    
    def _extract_person_name(self, query: str) -> Optional[str]:
        """Extract person name from query."""
        # Remove common question words and punctuation
        stop_words = ['what', 'is', 'the', 'phone', 'number', 'of', 'email', 
                     'contact', 'sir', 'madam', 'teacher', 'who', 'which',
                     'where', 'when', 'how', 'give', 'me', 'get', 'find']
        
        # Clean the query
        import re
        # Remove punctuation except dots (for Md., Dr., etc.)
        cleaned = re.sub(r'[^\w\s.]', ' ', query)
        words = cleaned.split()
        
        name_words = []
        
        for word in words:
            # Skip stop words
            if word.lower() in stop_words:
                continue
            # Skip very short words (but keep initials like "A" if followed by dot)
            if len(word) < 2 and '.' not in word:
                continue
            # Keep words that start with capital letter or contain dots (like Md.)
            if word and (word[0].isupper() or '.' in word):
                name_words.append(word)
        
        # Need at least one word that looks like a name
        if name_words:
            return ' '.join(name_words)
        
        return None


# =============================================================================
# Module-level function for easy import
# =============================================================================

_generator = SQLQueryGenerator()

def generate_sql_query(query: str) -> Tuple[Optional[str], str]:
    """
    Generate SQL query from natural language.
    
    Args:
        query: Natural language query (already normalized/translated)
        
    Returns:
        Tuple of (sql_query, query_type)
        - sql_query: Generated SQL string or None if out of scope
        - query_type: Type of query detected
    """
    return _generator.generate(query)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    test_cases = [
        "Who is the Chief Instructor of the CST 2nd shift?",
        "Who is the Chief Instructor of the CST Day shift?",
        "List all teachers in CST department",
        "How many teachers are in CST?",
        "What is the phone number of Rejuanul Arefin?",
        "List all departments",
        "How many total teachers are in CNPI?",
        "Give me the latest notices",  # Out of scope
    ]
    
    print("=" * 80)
    print("Testing Rule-Based SQL Query Generator")
    print("=" * 80)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n{i}. Query: {query}")
        sql, query_type = generate_sql_query(query)
        print(f"   Type: {query_type}")
        if sql:
            print(f"   SQL:\n{sql}")
        else:
            print(f"   Result: OUT OF SCOPE")
