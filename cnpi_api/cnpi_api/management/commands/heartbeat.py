"""
Django management command for heartbeat service.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send heartbeat ping to external service"

    def add_arguments(self, parser):
        parser.add_argument(
            '-t', '--target',
            type=str,
            default=None,
            help='Target URL to ping. If not provided, uses HEARTBEAT_TARGET_URL env var'
        )

    def handle(self, *args, **options):
        target_url = options.get('target') or os.getenv('HEARTBEAT_TARGET_URL')

        if not target_url:
            self.stdout.write(self.style.WARNING('HEARTBEAT_TARGET_URL not configured'))
            return

        try:
            self.stdout.write(f"Sending heartbeat to {target_url} at {datetime.now()}")
            response = requests.get(target_url, timeout=5)
            response.raise_for_status()
            self.stdout.write(self.style.SUCCESS(f"Heartbeat successful (HTTP {response.status_code})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Heartbeat failed: {e}"))