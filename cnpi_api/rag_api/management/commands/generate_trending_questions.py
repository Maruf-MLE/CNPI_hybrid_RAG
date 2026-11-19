"""
Django Management Command: Generate Trending Questions
======================================================
Run: python manage.py generate_trending_questions
"""

from django.core.management.base import BaseCommand
import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, '..', 'Cnpi_RAG'))

from nodes.trending_questions_generator import generate_and_save_trending_questions


class Command(BaseCommand):
    help = 'Generate trending questions from latest documents'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Generating trending questions...'))
        
        try:
            generate_and_save_trending_questions()
            self.stdout.write(self.style.SUCCESS('✅ Trending questions generated successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise
