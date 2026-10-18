"""
Django Admin Configuration for WhatsApp Bot

Provides admin interface for managing messages and conversations.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import WhatsAppMessage, WhatsAppConversation


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    """Admin interface for WhatsApp messages."""
    
    list_display = [
        'message_id_short',
        'phone_number',
        'sender_name',
        'status_badge',
        'message_preview',
        'received_at',
        'processed_at'
    ]
    
    list_filter = [
        'status',
        'message_type',
        'received_at',
        'processed_at'
    ]
    
    search_fields = [
        'message_id',
        'phone_number',
        'sender_name',
        'message_text',
        'response_text'
    ]
    
    readonly_fields = [
        'message_id',
        'phone_number',
        'sender_name',
        'message_type',
        'received_at',
        'processed_at',
        'response_sent_at',
        'formatted_payload'
    ]
    
    fieldsets = (
        ('Message Information', {
            'fields': (
                'message_id',
                'phone_number',
                'sender_name',
                'message_type',
                'received_at'
            )
        }),
        ('Content', {
            'fields': (
                'message_text',
                'response_text',
            )
        }),
        ('Processing Status', {
            'fields': (
                'status',
                'processed_at',
                'response_sent_at',
                'error_message',
            )
        }),
        ('Debug Information', {
            'classes': ('collapse',),
            'fields': (
                'formatted_payload',
            )
        }),
    )
    
    date_hierarchy = 'received_at'
    
    ordering = ['-received_at']
    
    actions = ['mark_for_retry']
    
    def message_id_short(self, obj):
        """Display shortened message ID."""
        return f"{obj.message_id[:12]}..." if len(obj.message_id) > 12 else obj.message_id
    message_id_short.short_description = 'Message ID'
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'received': '#3498db',      # blue
            'processing': '#f39c12',    # orange
            'completed': '#27ae60',     # green
            'failed': '#e74c3c',        # red
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def message_preview(self, obj):
        """Display message preview."""
        max_length = 50
        text = obj.message_text[:max_length]
        if len(obj.message_text) > max_length:
            text += '...'
        return text
    message_preview.short_description = 'Message'
    
    def formatted_payload(self, obj):
        """Display formatted JSON payload."""
        if obj.raw_payload:
            try:
                formatted = json.dumps(obj.raw_payload, indent=2, ensure_ascii=False)
                return format_html('<pre style="max-width: 800px; overflow: auto;">{}</pre>', formatted)
            except:
                return str(obj.raw_payload)
        return '-'
    formatted_payload.short_description = 'Raw Payload'
    
    def mark_for_retry(self, request, queryset):
        """Admin action to retry failed messages."""
        from .tasks import process_whatsapp_message
        
        count = 0
        for message in queryset.filter(status=WhatsAppMessage.STATUS_FAILED):
            message.status = WhatsAppMessage.STATUS_RECEIVED
            message.error_message = None
            message.save(update_fields=['status', 'error_message'])
            
            # Process in background
            import threading
            thread = threading.Thread(
                target=process_whatsapp_message,
                args=(message.id,),
                daemon=True
            )
            thread.start()
            count += 1
        
        self.message_user(request, f'Initiated retry for {count} message(s).')
    mark_for_retry.short_description = 'Retry selected failed messages'


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    """Admin interface for WhatsApp conversations."""
    
    list_display = [
        'phone_number',
        'user_name',
        'message_count',
        'history_length',
        'last_message_at',
        'created_at'
    ]
    
    search_fields = [
        'phone_number',
        'user_name'
    ]
    
    readonly_fields = [
        'phone_number',
        'created_at',
        'last_message_at',
        'formatted_history'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': (
                'phone_number',
                'user_name',
            )
        }),
        ('Statistics', {
            'fields': (
                'message_count',
                'created_at',
                'last_message_at',
            )
        }),
        ('Conversation History', {
            'fields': (
                'formatted_history',
            )
        }),
    )
    
    date_hierarchy = 'last_message_at'
    
    ordering = ['-last_message_at']
    
    actions = ['clear_history', 'export_conversations']
    
    def history_length(self, obj):
        """Display number of messages in history."""
        return len(obj.chat_history) if obj.chat_history else 0
    history_length.short_description = 'History Length'
    
    def formatted_history(self, obj):
        """Display formatted conversation history."""
        if not obj.chat_history:
            return 'No messages'
        
        html = '<div style="max-height: 600px; overflow-y: auto; padding: 10px; background: #f5f5f5; border-radius: 5px;">'
        
        for msg in obj.chat_history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            if role == 'user':
                bg_color = '#e3f2fd'
                role_label = '👤 User'
            else:
                bg_color = '#f1f8e9'
                role_label = '🤖 Bot'
            
            html += f'''
            <div style="margin-bottom: 10px; padding: 10px; background: {bg_color}; border-radius: 5px;">
                <div style="font-weight: bold; margin-bottom: 5px;">{role_label}</div>
                <div style="margin-bottom: 5px;">{content}</div>
                <div style="font-size: 0.8em; color: #666;">{timestamp}</div>
            </div>
            '''
        
        html += '</div>'
        return mark_safe(html)
    formatted_history.short_description = 'Chat History'
    
    def clear_history(self, request, queryset):
        """Admin action to clear conversation history."""
        count = queryset.update(chat_history=[], message_count=0)
        self.message_user(request, f'Cleared history for {count} conversation(s).')
    clear_history.short_description = 'Clear conversation history'
    
    def export_conversations(self, request, queryset):
        """Admin action to export conversations (placeholder)."""
        # This can be extended to export to CSV or JSON
        self.message_user(request, 'Export functionality can be implemented here.')
    export_conversations.short_description = 'Export selected conversations'
    
    def has_add_permission(self, request):
        """Disable manual creation of conversations."""
        return False
