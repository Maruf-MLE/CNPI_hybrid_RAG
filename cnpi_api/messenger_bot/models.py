from __future__ import annotations

from django.db import models


class ProcessedMessage(models.Model):
    """Track already-processed Messenger message IDs to prevent duplicate processing."""

    mid = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Facebook Messenger message ID (mid)",
    )
    psid = models.CharField(
        max_length=64,
        help_text="Page-Scoped User ID of the sender",
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "messenger_bot"
        verbose_name = "Processed Message"
        verbose_name_plural = "Processed Messages"

    def __str__(self) -> str:
        return f"{self.mid} ({self.psid})"
