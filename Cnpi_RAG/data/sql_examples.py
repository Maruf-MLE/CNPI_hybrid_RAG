"""
SQL Query Examples for Embedding-Based Generation
==================================================

This file contains example queries and their corresponding SQL statements.
These will be embedded and stored in the database for similarity search.
"""

SQL_EXAMPLES = [
    # Chief Instructor queries
    {
        "question": "Who is the Chief Instructor of CST department?",
        "sql_template": "SELECT p.name_en, p.name_bn, p.phone_primary, p.phone_secondary FROM people p JOIN departments d ON p.department_id = d.department_id WHERE UPPER(d.short_code) = '{department}' AND p.is_chief_instructor = TRUE;",
        "parameters": ["department"],
        "category": "chief_instructor"
    },
    {
        "question": "Who is the Chief Instructor of CST 2nd shift?",
        "sql_template": "SELECT p.name_en, p.name_bn, p.phone_primary, p.phone_secondary FROM people p JOIN departments d ON p.department_id = d.department_id WHERE UPPER(d.short_code) = '{department}' AND p.shift = '{shift}' AND p.is_chief_instructor = TRUE;",
        "parameters": ["department", "shift"],
        "category": "chief_instructor_shift"
    },
    {
        "question": "Who is the Chief Instructor of CST morning shift?",
        "sql_template": "SELECT p.name_en, p.name_bn, p.phone_primary, p.phone_secondary FROM people p JOIN departments d ON p.department_id = d.department_id WHERE UPPER(d.short_code) = '{department}' AND p.shift = '{shift}' AND p.is_chief_instructor = TRUE;",
        "parameters": ["department", "shift"],
        "category": "chief_instructor_shift"
    },
    
    # Teacher list queries
    {
        "question": "List all teachers in CST department",
        "sql_template": "SELECT p.name_en, p.name_bn, des.title_en, des.title_bn FROM people p JOIN departments d ON p.department_id = d.department_id LEFT JOIN designations des ON p.designation_id = des.designation_id WHERE UPPER(d.short_code) = '{department}' AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');",
        "parameters": ["department"],
        "category": "teacher_list"
    },
    {
        "question": "Show me all teachers in ET department",
        "sql_template": "SELECT p.name_en, p.name_bn, des.title_en, des.title_bn FROM people p JOIN departments d ON p.department_id = d.department_id LEFT JOIN designations des ON p.designation_id = des.designation_id WHERE UPPER(d.short_code) = '{department}' AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');",
        "parameters": ["department"],
        "category": "teacher_list"
    },
    
    # Teacher count queries
    {
        "question": "How many teachers are in CST department?",
        "sql_template": "SELECT COUNT(*) AS total FROM people p JOIN departments d ON p.department_id = d.department_id JOIN designations des ON p.designation_id = des.designation_id WHERE UPPER(d.short_code) = '{department}' AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');",
        "parameters": ["department"],
        "category": "teacher_count"
    },
    {
        "question": "Total number of teachers in RAC",
        "sql_template": "SELECT COUNT(*) AS total FROM people p JOIN departments d ON p.department_id = d.department_id JOIN designations des ON p.designation_id = des.designation_id WHERE UPPER(d.short_code) = '{department}' AND des.category IN ('Academic Leadership', 'Teacher', 'Craft Instructor');",
        "parameters": ["department"],
        "category": "teacher_count"
    },
    
    # Person contact queries
    {
        "question": "What is the phone number of Rejuanul Arefin?",
        "sql_template": "SELECT p.name_en, p.name_bn, d.name_en AS department, des.title_en AS designation, p.phone_primary, p.phone_secondary, p.email FROM people p LEFT JOIN departments d ON p.department_id = d.department_id LEFT JOIN designations des ON p.designation_id = des.designation_id WHERE p.name_en %% '{name}' ORDER BY similarity(p.name_en, '{name}') DESC LIMIT 5;",
        "parameters": ["name"],
        "category": "person_contact"
    },
    {
        "question": "Phone number of Md. Jewel Rana",
        "sql_template": "SELECT p.name_en, p.name_bn, d.name_en AS department, des.title_en AS designation, p.phone_primary, p.phone_secondary, p.email FROM people p LEFT JOIN departments d ON p.department_id = d.department_id LEFT JOIN designations des ON p.designation_id = des.designation_id WHERE p.name_en %% '{name}' ORDER BY similarity(p.name_en, '{name}') DESC LIMIT 5;",
        "parameters": ["name"],
        "category": "person_contact"
    },
    {
        "question": "Email address of Subel Ali",
        "sql_template": "SELECT p.name_en, p.name_bn, d.name_en AS department, des.title_en AS designation, p.phone_primary, p.phone_secondary, p.email FROM people p LEFT JOIN departments d ON p.department_id = d.department_id LEFT JOIN designations des ON p.designation_id = des.designation_id WHERE p.name_en %% '{name}' ORDER BY similarity(p.name_en, '{name}') DESC LIMIT 5;",
        "parameters": ["name"],
        "category": "person_contact"
    },
    
    # Department list queries
    {
        "question": "List all departments",
        "sql_template": "SELECT name_en, name_bn, short_code, shift_info, total_teachers, total_labs FROM departments ORDER BY short_code;",
        "parameters": [],
        "category": "department_list"
    },
    {
        "question": "Show all departments in CNPI",
        "sql_template": "SELECT name_en, name_bn, short_code, shift_info, total_teachers, total_labs FROM departments ORDER BY short_code;",
        "parameters": [],
        "category": "department_list"
    },
    
    # Institution statistics
    {
        "question": "How many total teachers are in CNPI?",
        "sql_template": "SELECT total_teachers FROM institutions WHERE short_name = 'CNPI';",
        "parameters": [],
        "category": "institution_teachers"
    },
    {
        "question": "Total students in the institution",
        "sql_template": "SELECT total_students FROM institutions WHERE short_name = 'CNPI';",
        "parameters": [],
        "category": "institution_students"
    },
    {
        "question": "How many staff members are there?",
        "sql_template": "SELECT total_staff FROM institutions WHERE short_name = 'CNPI';",
        "parameters": [],
        "category": "institution_staff"
    },
    {
        "question": "Total workforce in CNPI",
        "sql_template": "SELECT total_workforce FROM institutions WHERE short_name = 'CNPI';",
        "parameters": [],
        "category": "institution_workforce"
    },
]
