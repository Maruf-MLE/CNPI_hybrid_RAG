"""
answer_bot/models.py
====================
Models for Answer Bot (separate from messenger_bot)
"""

from django.db import models


class ProcessedAnswerMessage(models.Model):
    """
    Duplicate guard for Answer Bot — stores processed message IDs (mid).
    
    Same structure as messenger_bot.ProcessedMessage but separate table.
    """
    mid = models.CharField(max_length=255, unique=True, db_index=True)
    psid = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'answer_bot_processed_messages'
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"AnswerMessage {self.mid[:20]}... from {self.psid}"
