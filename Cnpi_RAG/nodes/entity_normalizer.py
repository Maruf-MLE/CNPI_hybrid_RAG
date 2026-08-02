import re

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

import sys
from pathlib import Path

# Ensure plan/ is importable so we can use the canonical state types
project_root = Path(__file__).resolve().parent.parent
plan_root = project_root.parent / "plan"
if str(plan_root) not in sys.path:
    sys.path.insert(0, str(plan_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import RAGState

# Example Alias Table
ALIAS_TABLE = [
    {
        "canonical": "CNPI",
        "aliases": [
            "cnpi", "CNPI", "chapainawabganj polytechnic institute", 
            "chapainawabganj politecnic institute", "চাঁপাইনবাবগঞ্জ পলিটেকনিক", 
            "চাঁপাইনবাবগঞ্জ পলিটেকনিক ইনস্টিটিউট"
        ]
    },
    {
        "canonical": "Teacher",
        "aliases": ["স্যার", "Teacher", "teacher"]
    },
    {
        "canonical": "Department",
        "aliases": ["বিভাগ", "Department", "department", "টেকনোলজি", "Technology", "technology", "dipertment"]
    },
    {
        "canonical": "Class",
        "aliases": ["বিষয়", "Subject", "subject", "পিরিয়ড", "Period", "period"]
    },
    {
        "canonical": "Routine",
        "aliases": ["routine", "Routine", "rutine", "রুটিন"]
    },
    {
        "canonical": "Phone",
        "aliases": ["মোবাইল", "Phone", "phone", "Mobile", "mobile", "ফোন নম্বর", "মোবাইল নম্বর", "যোগাযোগের নম্বর"]
    },
    {
        "canonical": "Address",
        "aliases": ["বাসস্থান", "বাড়ি", "Address", "address", "ঠিকানায়"]
    },
    {
        "canonical": "Day Shift",
        "aliases": ["Day Shift", "day shift", "2nd shift", "second shift"]
    },
    {
        "canonical": "Morning Shift",
        "aliases": ["Morning Shift", "morning shift", "1st shift", "first shift"]
    },
    {
        "canonical": "CST",
        "aliases": [
            "cst", "Computer", "computer", "Computer Science", "computer science", 
            "Computer Science and Technology", "computer science and technology", 
            "কম্পিউটার", "কম্পিউটার বিজ্ঞান", "কম্পিউটার সায়েন্স"
        ]
    },
    {
        "canonical": "ET",
        "aliases": [
            "et", "Electrical", "electrical", "Electrical Technology", 
            "electrical technology", "ইলেকট্রিক্যাল"
        ]
    },
    {
        "canonical": "ENT",
        "aliases": [
            "ent", "Electronics", "electronics", "Electronics Technology", 
            "electronics technology", "ইলেকট্রনিক্স"
        ]
    },
    {
        "canonical": "MNT",
        "aliases": [
            "mnt", "Mechatronics", "mechatronics", "Mechatronics Technology", 
            "mechatronics technology", "মেকাট্রনিক্স"
        ]
    },
    {
        "canonical": "FT",
        "aliases": [
            "ft", "Food", "food", "Food Technology", "food technology", "ফুড"
        ]
    },
    {
        "canonical": "RAC",
        "aliases": [
            "rac", "Refrigeration", "refrigeration", "Air Conditioning", 
            "air conditioning", "Refrigeration and Air Conditioning Technology", 
            "refrigeration and air conditioning technology", "রেফ্রিজারেশন"
        ]
    },
    {
        "canonical": "Sunday",
        "aliases": ["Sunday", "sunday", "রবিবার", "robibar"]
    },
    {
        "canonical": "Monday",
        "aliases": ["Monday", "monday", "সোমবার", "sombar"]
    },
    {
        "canonical": "Tuesday",
        "aliases": ["Tuesday", "tuesday", "মঙ্গলবার", "mongolbar"]
    },
    {
        "canonical": "Wednesday",
        "aliases": ["Wednesday", "wednesday", "বুধবার", "budhbar"]
    },
    {
        "canonical": "Thursday",
        "aliases": ["Thursday", "thursday", "বৃহস্পতিবার", "brihospotibar"]
    },
    {
        "canonical": "Friday",
        "aliases": ["Friday", "friday", "শুক্রবার", "shukrabar"]
    },
    {
        "canonical": "Saturday",
        "aliases": ["Saturday", "saturday", "শনিবার", "shonibar"]
    },
    {
            "canonical": "Chief instructor",
            "aliases": ["CI", "Dipertment head", "bivagiyo prodhan","ci"]
        },
    {
            "canonical": "VC",
            "aliases": ["Vice", "Vice principal","vc"]
        }
]

def normalize_entities(query: str, alias_table: list[dict]) -> str:
    """
    Normalizes entities in the given query based on the alias_table.
    Does not use LLMs.
    """
    if not query or not query.strip():
        return ""
        
    normalized_query = query
    
    for entity in alias_table:
        canonical = entity["canonical"]
        aliases = entity["aliases"]
        
        aliases_sorted = sorted(aliases, key=len, reverse=True)
        exact_matched = False
        
        # Step 2: Exact Match
        for alias in aliases_sorted:
            # Word boundary matching that handles non-English words properly.
            # Using \b might not work well for Bengali, so we use string matching where 
            # characters before/after are not alphanumeric.
            pattern = re.compile(rf'(?<![a-zA-Z0-9_\u0980-\u09FF]){re.escape(alias)}(?![a-zA-Z0-9_\u0980-\u09FF])', flags=re.IGNORECASE)
            
            if pattern.search(normalized_query):
                normalized_query = pattern.sub(canonical, normalized_query)
                exact_matched = True
                
        # Step 3: Fuzzy Match (if no exact match found for this entity)
        if not exact_matched and fuzz is not None:
            words = list(re.finditer(r'\S+', normalized_query))
            
            for alias in aliases_sorted:
                alias_word_count = len(alias.split())
                
                # Cannot use sliding window if words are fewer than alias length, but let's allow partial fallback?
                # Actually, just window exact size
                match_found_in_fuzz = False
                for i in range(len(words) - alias_word_count + 1):
                    window = words[i:i+alias_word_count]
                    window_text = normalized_query[window[0].start():window[-1].end()]
                    
                    similarity = fuzz.ratio(window_text.lower(), alias.lower())
                    
                    if similarity >= 90:
                        # Replace window text
                        normalized_query = normalized_query[:window[0].start()] + canonical + normalized_query[window[-1].end():]
                        match_found_in_fuzz = True
                        break # Break to re-evaluate after string mutation
                
                if match_found_in_fuzz:
                    # multiple aliases for same entity won't be replaced again since we break
                    break

    return normalized_query

def entity_normalizer_node(state: RAGState) -> dict:
    """
    LangGraph Node to normalize entities in the rewritten query.
    """
    rewritten_query = state.get("rewritten_query") or state.get("user_input", "")
    
    try:
        normalized_query = normalize_entities(rewritten_query, ALIAS_TABLE)
    except Exception as e:
        print(f"Entity normalization error: {e}")
        normalized_query = rewritten_query  # Fallback to original

    return {"rewritten_query": normalized_query, "normalized_query": normalized_query}

# Testing locally
if __name__ == "__main__":
    print(normalize_entities("CNPI te CST teacher koyjon?", ALIAS_TABLE))
    print(normalize_entities("chapainababjang polytechnic", ALIAS_TABLE))
    print(normalize_entities("Computer teacher", ALIAS_TABLE))
