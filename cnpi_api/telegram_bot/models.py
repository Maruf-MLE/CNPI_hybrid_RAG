"""
telegram_bot/models.py
======================
Models for Telegram Bot - stores processed message IDs to prevent duplicates.

This model structure follows the same pattern as answer_bot but adapted for Telegram.
"""

from django.db import models


class ProcessedTelegramMessage(models.Model):
    """
    Duplicate guard for Telegram Bot — stores processed message IDs.
    
    Telegram message IDs are unique within a chat, so we store both
    chat_id and message_id as a compound unique constraint.
    """
    chat_id = models.BigIntegerField(db_index=True, help_text="Telegram chat ID")
    message_id = models.BigIntegerField(help_text="Telegram message ID")
    user_id = models.BigIntegerField(db_index=True, help_text="Telegram user ID")
    username = models.CharField(max_length=255, blank=True, null=True, help_text="Telegram username (optional)")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'telegram_bot_processed_messages'
        unique_together = [['chat_id', 'message_id']]
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['chat_id', 'created_at']),
        ]

    def __str__(self):
        return f"TelegramMessage chat={self.chat_id} msg={self.message_id} from user={self.user_id}"
