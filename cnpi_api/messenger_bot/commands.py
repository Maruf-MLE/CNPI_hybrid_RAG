"""
messenger_bot/commands.py
=========================
Handle bot commands like /help, /priority, /stats
"""

from __future__ import annotations

import logging
from typing import Any

from admin_panel import services as admin_services

logger = logging.getLogger(__name__)


def is_command(text: str) -> bool:
    """Check if message is a bot command."""
    return text.startswith("/")


def handle_command(psid: str, text: str, send_reply_fn) -> dict[str, Any] | None:
    """
    Handle bot command and return result or None if not a command.
    
    Args:
        psid: User's Page-Scoped ID
        text: Message text
        send_reply_fn: Function to send reply to user
        
    Returns:
        Command result dict or None if not handled
    """
    if not is_command(text):
        return None
    
    command = text.split()[0].lower()
    args = text.split()[1:] if len(text.split()) > 1 else []
    
    if command == "/help":
        return _handle_help(psid, send_reply_fn)
    elif command == "/priority":
        return {"type": "priority", "args": args}
    elif command == "/stats":
        return _handle_stats(psid, send_reply_fn)
    elif command == "/ping":
        send_reply_fn(psid, "🏓 Pong! Bot is active.")
        return {"handled": True}
    else:
        send_reply_fn(psid, f"❓ Unknown command: {command}\n\nType /help for available commands.")
        return {"handled": True}


def _handle_help(psid: str, send_reply_fn) -> dict[str, Any]:
    """Send help message with available commands."""
    help_text = """📚 **Available Commands:**

/help — Show this help message
/priority — Mark next message as priority document
/stats — Show your message statistics
/ping — Check if bot is active

**How to use:**
• Send text or image — saved as notice
• Send image with caption — OCR + caption saved
• Send /priority then your message — saved as priority document

**Example:**
Send: "আগামীকাল ছুটি"
Reply: ✅ Saved (doc_id: 123)"""
    
    send_reply_fn(psid, help_text)
    return {"handled": True}


def _handle_stats(psid: str, send_reply_fn) -> dict[str, Any]:
    """Show user's message statistics."""
    try:
        # Count documents from this user (source_file = messenger_bot, meta contains psid)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM documents 
                WHERE source_file = 'messenger_bot'
                  AND meta::text LIKE %s
            """, [f'%"psid": "{psid}"%'])
            count = cursor.fetchone()[0]
        
        stats_text = f"""📊 **Your Statistics:**

Total messages saved: {count}
Source: Messenger Bot
PSID: {psid[:8]}...{psid[-4:]}

Thank you for contributing to the knowledge base! 🙏"""
        
        send_reply_fn(psid, stats_text)
        return {"handled": True}
    except Exception as e:
        logger.error("Stats error: %s", e)
        send_reply_fn(psid, "❌ Could not fetch stats.")
        return {"handled": True}
