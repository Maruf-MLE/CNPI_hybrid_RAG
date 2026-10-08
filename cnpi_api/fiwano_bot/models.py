"""
Fiwano Messenger Bot Models
============================

Stores incoming messages, conversation history, and processing status.
"""

from django.db import models
from django.utils import timezone


class FiwanoInboundMessage(models.Model):
    """
    Fiwano থেকে আসা প্রতিটি message track করে।
    message_id দিয়ে idempotency ensure করা হয়।
    """
    
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('share', 'Share'),
        ('unsupported', 'Unsupported'),
    ]
    
    # Fiwano identifiers
    message_id = models.CharField(max_length=255, unique=True, db_index=True)
    channel_id = models.CharField(max_length=255, db_index=True)
    channel_type = models.CharField(max_length=50)  # messenger, whatsapp, instagram
    
    # Sender info
    sender_id = models.CharField(max_length=255, db_index=True)  # PSID for Messenger
    sender_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Message content
    message_type = models.CharField(max_length=50, choices=MESSAGE_TYPE_CHOICES)
    message_text = models.TextField(blank=True)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    
    # AI response
    response_text = models.TextField(blank=True)
    response_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Raw payload for debugging
    raw_payload = models.JSONField(default=dict)
    
    # Timestamps
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['channel_id', 'sender_id', '-received_at']),
            models.Index(fields=['status', 'received_at']),
        ]
    
    def __str__(self):
        return f"{self.message_id} - {self.sender_id} - {self.status}"
    
    def mark_processing(self):
        """Mark as processing."""
        self.status = 'processing'
        self.save(update_fields=['status'])
    
    def mark_completed(self, response_text):
        """Mark as completed with response."""
        self.status = 'completed'
        self.response_text = response_text
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'response_text', 'processed_at'])
    
    def mark_failed(self, error_message):
        """Mark as failed with error."""
        self.status = 'failed'
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'processed_at', 'retry_count'])


class FiwanoConversation(models.Model):
    """
    প্রতিটি user-এর সাথে conversation track করে।
    Chat history এখানে store হয়।
    """
    
    channel_id = models.CharField(max_length=255)
    sender_id = models.CharField(max_length=255)
    
    # Conversation metadata
    first_message_at = models.DateTimeField(default=timezone.now)
    last_message_at = models.DateTimeField(default=timezone.now)
    message_count = models.IntegerField(default=0)
    
    # Chat history (langchain messages format)
    chat_history = models.JSONField(default=list)
    
    class Meta:
        unique_together = [['channel_id', 'sender_id']]
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['channel_id', 'sender_id']),
            models.Index(fields=['-last_message_at']),
        ]
    
    def __str__(self):
        return f"{self.channel_id} - {self.sender_id} ({self.message_count} messages)"
    
    def add_message(self, role: str, content: str):
        """Add a message to chat history."""
        self.chat_history.append({
            'role': role,
            'content': content,
            'timestamp': timezone.now().isoformat()
        })
        self.message_count += 1
        self.last_message_at = timezone.now()
        self.save(update_fields=['chat_history', 'message_count', 'last_message_at'])
    
    def get_history_for_rag(self):
        """
        Convert chat history to langchain BaseMessage format.
        """
        from langchain_core.messages import HumanMessage, AIMessage
        
        messages = []
        for msg in self.chat_history[-10:]:  # Last 10 messages only
            role = msg.get('role')
            content = msg.get('content', '')
            
            if role == 'human':
                messages.append(HumanMessage(content=content))
            elif role == 'ai':
                messages.append(AIMessage(content=content))
        
        return messages
