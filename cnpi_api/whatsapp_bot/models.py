"""
Database models for WhatsApp bot.

Models for tracking messages, conversations, and user interactions.
"""

from django.db import models
from django.utils import timezone
from langchain_core.messages import HumanMessage, AIMessage


class WhatsAppMessage(models.Model):
    """
    Track individual WhatsApp messages for duplicate prevention and debugging.
    
    This model stores all incoming messages from WhatsApp with their processing
    status to ensure idempotent handling and provide audit trails.
    """
    
    # Message Status Choices
    STATUS_RECEIVED = 'received'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_RECEIVED, 'Received'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    # Core fields
    message_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique message ID from WhatsApp"
    )
    
    # Sender information
    phone_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Sender's phone number with country code"
    )
    
    sender_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Sender's profile name (if available)"
    )
    
    # Message content
    message_text = models.TextField(
        help_text="Original message text from user"
    )
    
    message_type = models.CharField(
        max_length=50,
        default='text',
        help_text="Type of message (text, image, document, etc.)"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RECEIVED,
        db_index=True,
        help_text="Current processing status of the message"
    )
    
    # Response data
    response_text = models.TextField(
        blank=True,
        null=True,
        help_text="Bot's response text sent to user"
    )
    
    response_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when response was sent"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error details if processing failed"
    )
    
    # Metadata
    raw_payload = models.JSONField(
        blank=True,
        null=True,
        help_text="Original webhook payload for debugging"
    )
    
    # Timestamps
    received_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When webhook received the message"
    )
    
    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When processing completed or failed"
    )
    
    class Meta:
        ordering = ['-received_at']
        verbose_name = 'WhatsApp Message'
        verbose_name_plural = 'WhatsApp Messages'
        indexes = [
            models.Index(fields=['phone_number', '-received_at']),
            models.Index(fields=['status', '-received_at']),
        ]
    
    def __str__(self):
        return f"{self.phone_number} - {self.message_id} ({self.status})"
    
    def mark_processing(self):
        """Mark message as currently being processed."""
        self.status = self.STATUS_PROCESSING
        self.save(update_fields=['status'])
    
    def mark_completed(self, response_text):
        """Mark message as successfully processed."""
        self.status = self.STATUS_COMPLETED
        self.response_text = response_text
        self.response_sent_at = timezone.now()
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'response_text', 'response_sent_at', 'processed_at'])
    
    def mark_failed(self, error_message):
        """Mark message as failed with error details."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processed_at'])


class WhatsAppConversation(models.Model):
    """
    Track conversation history for context-aware responses.
    
    Stores chat history per user to maintain conversational context
    across multiple message exchanges.
    """
    
    # User identification
    phone_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="User's phone number (unique per conversation)"
    )
    
    user_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="User's display name"
    )
    
    # Conversation data
    chat_history = models.JSONField(
        default=list,
        help_text="List of message dictionaries for conversation context"
    )
    
    # Statistics
    message_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of messages in this conversation"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When conversation was first created"
    )
    
    last_message_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp of most recent message"
    )
    
    class Meta:
        ordering = ['-last_message_at']
        verbose_name = 'WhatsApp Conversation'
        verbose_name_plural = 'WhatsApp Conversations'
    
    def __str__(self):
        return f"{self.phone_number} - {self.message_count} messages"
    
    def add_user_message(self, message_text):
        """
        Add a user message to conversation history.
        
        Args:
            message_text: The user's message content
        """
        message_entry = {
            'role': 'user',
            'content': message_text,
            'timestamp': timezone.now().isoformat()
        }
        self.chat_history.append(message_entry)
        self.message_count += 1
        self.save(update_fields=['chat_history', 'message_count', 'last_message_at'])
    
    def add_bot_message(self, response_text):
        """
        Add a bot response to conversation history.
        
        Args:
            response_text: The bot's response content
        """
        message_entry = {
            'role': 'assistant',
            'content': response_text,
            'timestamp': timezone.now().isoformat()
        }
        self.chat_history.append(message_entry)
        self.save(update_fields=['chat_history', 'last_message_at'])
    
    def get_history_for_rag(self, max_messages=10):
        """
        Get recent chat history formatted for RAG system.
        
        Args:
            max_messages: Maximum number of messages to return (default: 10)
        
        Returns:
            List of LangChain message objects (HumanMessage, AIMessage)
        """
        recent_history = self.chat_history[-max_messages:] if len(self.chat_history) > max_messages else self.chat_history
        
        formatted_history = []
        for msg in recent_history:
            if msg['role'] == 'user':
                formatted_history.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                formatted_history.append(AIMessage(content=msg['content']))
        
        return formatted_history
    
    def clear_old_history(self, keep_last=20):
        """
        Clear old messages to prevent unlimited growth.
        
        Args:
            keep_last: Number of recent messages to keep (default: 20)
        """
        if len(self.chat_history) > keep_last:
            self.chat_history = self.chat_history[-keep_last:]
            self.save(update_fields=['chat_history'])
