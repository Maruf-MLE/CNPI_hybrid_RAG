"""
Trending Questions Generator Node for LangGraph RAG Pipeline
=============================================================
Generates relevant Bengali questions from latest documents content.
"""

import os
import logging
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# System prompt components
CORE_INSTRUCTIONS = """## Layer 1: Core Instructions (Immutable)

আপনি একজন বাংলা প্রশ্ন তৈরির বিশেষজ্ঞ। আপনার কাজ হলো প্রদত্ত নথির বিষয়বস্তু বিশ্লেষণ করে সারসংক্ষেপ-ধরনের প্রশ্ন তৈরি করা।

### কঠোর নিয়মাবলী

1. প্রতিটি প্রশ্ন সম্পূর্ণ বাংলায় লিখুন।
2. প্রতিটি প্রশ্ন সংক্ষিপ্ত রাখুন—সর্বোচ্চ ৮–১০ শব্দ।
3. প্রশ্নগুলো সারসংক্ষেপ-ধরনের হতে হবে, যেন একটি প্রশ্নের উত্তরে নথির মূল বিষয়ের সব গুরুত্বপূর্ণ তথ্য পাওয়া যায়।
4. হ্যাঁ/না-সূচক প্রশ্ন তৈরি করবেন না; তথ্যমূলক প্রশ্ন তৈরি করুন।
5. প্রতিটি নথির জন্য ঠিক একটি প্রশ্ন তৈরি করুন।
6. আউটপুটে শুধু প্রশ্নগুলো থাকবে। প্রতিটি প্রশ্ন নতুন লাইনে লিখুন।
7. কোনো নম্বর, বুলেট, ব্যাখ্যা বা অতিরিক্ত টেক্সট দেবেন না।"""

PROJECT_CONFIGURATION = """## Layer 2: Project Configuration (Configurable)

### প্রতিষ্ঠানের নাম ব্যবহারের নিয়ম

1. "চাঁপাইনবাবগঞ্জ সরকারি পলিটেকনিক ইনস্টিটিউট"-এর পরিবর্তে সবসময় "CNPI" লিখুন।
2. "কুমিল্লা পলিটেকনিক ইনস্টিটিউট"-এর পরিবর্তে সবসময় "CNPI" লিখুন।
3. যেকোনো দীর্ঘ প্রতিষ্ঠানের নামের পরিবর্তে তার সংক্ষিপ্ত রূপ ব্যবহার করুন।"""

EXAMPLES_REFERENCE = """## Layer 3: Examples & Reference (Configurable)

### ভুল উদাহরণ

❌ "চাঁপাইনবাবগঞ্জ সরকারি পলিটেকনিক ইনস্টিটিউটে 'মিট-আপ ২০২৬' অনুষ্ঠানটি কী কী উদ্দেশ্যে আয়োজন করা হয়েছে?"

### সঠিক উদাহরণ

✅ "CNPI মিট-আপ ২০২৬ সম্পর্কে কী জানা দরকার?"
✅ "CNPI-তে ভর্তির যোগ্যতা কী?"
✅ "CNPI-র ক্লাস রুটিন কেমন?"
✅ "CNPI-তে কোন বিভাগগুলো আছে?"
✅ "CNPI-র পরীক্ষার সময়সূচি কখন?" """

TRENDING_QUESTIONS_SYSTEM_PROMPT = f"{CORE_INSTRUCTIONS}\n\n{PROJECT_CONFIGURATION}\n\n{EXAMPLES_REFERENCE}"


def generate_trending_questions(latest_documents: List[Dict[str, Any]]) -> List[str]:
    """
    Generate Bengali questions from latest document contents.
    
    Args:
        latest_documents: List of document dicts with 'content', 'doc_type', 'topic'
        
    Returns:
        List of generated Bengali questions
    """
    if not latest_documents:
        logger.warning("No documents provided for question generation")
        return []
    
    # Initialize Gemini LLM
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not found")
        return []
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",  # ← Using same model as project
        google_api_key=gemini_api_key,
        temperature=0.7,
    )
    
    # Prepare context from documents
    doc_contexts = []
    for idx, doc in enumerate(latest_documents[:5], 1):
        content_preview = doc.get('content', '')[:500]  # First 500 chars
        doc_type = doc.get('doc_type', 'general')
        topic = doc.get('topic', 'সাধারণ')
        
        doc_contexts.append(f"""
নথি {idx}:
ধরন: {doc_type}
বিষয়: {topic}
বিষয়বস্তু: {content_preview}...
""")
    
    combined_context = "\n".join(doc_contexts)
    
    # Question generation prompt
    system_prompt = SystemMessage(content=TRENDING_QUESTIONS_SYSTEM_PROMPT)
    
    user_prompt = HumanMessage(content=f"""
নিম্নলিখিত সর্বশেষ নথিগুলো থেকে 5টি প্রাসঙ্গিক বাংলা প্রশ্ন তৈরি করুন:

{combined_context}

প্রতিটি নথির মূল বিষয় থেকে একটি করে স্পষ্ট এবং আকর্ষণীয় প্রশ্ন তৈরি করুন।
""")
    
    try:
        # Generate questions
        response = llm.invoke([system_prompt, user_prompt])
        
        # Parse response - handle both string and list content
        content = response.content
        if isinstance(content, list):
            # Extract text from content blocks
            questions_text = ""
            for block in content:
                if isinstance(block, dict):
                    questions_text += block.get("text", "")
                else:
                    questions_text += str(block)
        else:
            questions_text = str(content)
        
        questions_text = questions_text.strip()
        
        questions = [
            q.strip() 
            for q in questions_text.split('\n') 
            if q.strip() and len(q.strip()) > 5
        ]
        
        # Take first 5 questions
        questions = questions[:5]
        
        logger.info(f"Generated {len(questions)} trending questions")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return []


def save_trending_questions_to_db(questions: List[str], source_doc_ids: List[int] = None):
    """
    Save generated questions to database.
    
    Args:
        questions: List of Bengali questions
        source_doc_ids: List of source document IDs (optional)
    """
    import psycopg2
    from psycopg2.extras import execute_values
    
    db_config = {
        'host': os.getenv('DB_HOST'),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': os.getenv('DB_PORT', '5432'),
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Deactivate old questions
        cur.execute("UPDATE trending_questions SET is_active = FALSE")
        
        # Insert new questions
        values = []
        for idx, question in enumerate(questions):
            source_id = source_doc_ids[idx] if source_doc_ids and idx < len(source_doc_ids) else None
            values.append((question, source_id, 1.0, 'general', True, 0))
        
        execute_values(
            cur,
            """
            INSERT INTO trending_questions 
            (question, source_doc_id, relevance_score, category, is_active, click_count)
            VALUES %s
            """,
            values
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Saved {len(questions)} trending questions to database")
        
    except Exception as e:
        logger.error(f"Error saving questions to database: {e}")


def fetch_latest_documents(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch latest documents from database.
    
    Args:
        limit: Number of documents to fetch
        
    Returns:
        List of document dictionaries
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    db_config = {
        'host': os.getenv('DB_HOST'),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': os.getenv('DB_PORT', '5432'),
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch latest documents
        cur.execute("""
            SELECT doc_id, content, doc_type, topic, department, 
                   meta, created_at
            FROM documents
            WHERE LENGTH(TRIM(content)) > 100
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        
        documents = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(doc) for doc in documents]
        
    except Exception as e:
        logger.error(f"Error fetching latest documents: {e}")
        return []


def generate_and_save_trending_questions():
    """
    Main function to generate and save trending questions.
    Call this from a cron job or management command.
    """
    logger.info("Starting trending questions generation...")
    
    # Fetch latest documents
    latest_docs = fetch_latest_documents(limit=5)
    
    if not latest_docs:
        logger.warning("No documents found for question generation")
        return
    
    # Generate questions
    questions = generate_trending_questions(latest_docs)
    
    if not questions:
        logger.warning("No questions generated")
        return
    
    # Save to database
    source_ids = [doc['doc_id'] for doc in latest_docs]
    save_trending_questions_to_db(questions, source_ids)
    
    logger.info(f"Trending questions generation complete. Generated {len(questions)} questions.")
