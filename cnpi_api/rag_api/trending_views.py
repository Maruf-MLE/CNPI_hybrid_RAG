"""
Trending Questions API Views
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import psycopg2
from psycopg2.extras import RealDictCursor
from django.conf import settings
import os

logger = logging.getLogger(__name__)


@api_view(["GET"])
def trending_questions_view(request):
    """GET /api/trending-questions/
    
    Returns 5 active trending questions.
    
    Response:
        {
            "questions": [
                {
                    "id": 1,
                    "question": "CST Department এর Chief Instructor কে?",
                    "category": "general",
                    "click_count": 5
                },
                ...
            ],
            "count": 5
        }
    """
    try:
        db_config = {
            'host': os.getenv('DB_HOST'),
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'port': os.getenv('DB_PORT', '5432'),
        }
        
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch active trending questions
        cur.execute("""
            SELECT id, question, category, click_count, created_at
            FROM trending_questions
            WHERE is_active = TRUE
            ORDER BY created_at DESC, click_count DESC
            LIMIT 5
        """)
        
        questions = cur.fetchall()
        cur.close()
        conn.close()
        
        questions_list = [
            {
                'id': q['id'],
                'question': q['question'],
                'category': q.get('category', 'general'),
                'click_count': q.get('click_count', 0),
            }
            for q in questions
        ]
        
        return Response({
            'questions': questions_list,
            'count': len(questions_list)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception("Error fetching trending questions")
        return Response(
            {
                'error': 'Failed to fetch trending questions',
                'detail': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def track_question_click(request, question_id):
    """POST /api/trending-questions/<id>/click/
    
    Track when a user clicks on a trending question.
    Increments click_count.
    """
    try:
        db_config = {
            'host': os.getenv('DB_HOST'),
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'port': os.getenv('DB_PORT', '5432'),
        }
        
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Increment click count
        cur.execute("""
            UPDATE trending_questions
            SET click_count = click_count + 1
            WHERE id = %s AND is_active = TRUE
            RETURNING id
        """, (question_id,))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if result:
            return Response({'success': True}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Question not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except Exception as e:
        logger.exception(f"Error tracking question click: {question_id}")
        return Response(
            {'error': 'Failed to track click', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
