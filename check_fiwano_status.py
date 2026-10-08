#!/usr/bin/env python
"""Check Fiwano message status"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, 'G:/CNPI_Hybrid_RAG/cnpi_api')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cnpi_api.settings')
django.setup()

from fiwano_bot.models import FiwanoInboundMessage

print("\n" + "="*60)
print("FIWANO MESSAGE STATUS")
print("="*60)

messages = FiwanoInboundMessage.objects.all().order_by('-received_at')[:5]

if not messages:
    print("\nNo messages found in database.")
else:
    for i, msg in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"Message ID: {msg.message_id[:30]}...")
        print(f"User PSID: {msg.sender_id}")
        print(f"Text: {msg.message_text}")
        print(f"Status: {msg.status}")
        print(f"Received: {msg.received_at}")
        print(f"Processed: {msg.processed_at or 'Not yet'}")
        
        if msg.response_text:
            print(f"Response: {msg.response_text[:200]}...")
        else:
            print("Response: (none)")
        
        if msg.error_message:
            print(f"ERROR: {msg.error_message}")
        
        print(f"Retry count: {msg.retry_count}")

print("\n" + "="*60)
