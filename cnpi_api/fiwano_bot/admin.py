from django.contrib import admin
from .models import FiwanoInboundMessage, FiwanoConversation


@admin.register(FiwanoInboundMessage)
class FiwanoInboundMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'sender_id', 'channel_type', 'status', 'received_at', 'processed_at']
    list_filter = ['status', 'channel_type', 'message_type', 'received_at']
    search_fields = ['message_id', 'sender_id', 'message_text', 'response_text']
    readonly_fields = ['message_id', 'channel_id', 'channel_type', 'sender_id', 
                       'received_at', 'processed_at', 'raw_payload']
    
    fieldsets = [
        ('Message Info', {
            'fields': ['message_id', 'channel_id', 'channel_type', 'sender_id', 'sender_name']
        }),
        ('Content', {
            'fields': ['message_type', 'message_text', 'response_text']
        }),
        ('Status', {
            'fields': ['status', 'error_message', 'retry_count']
        }),
        ('Timestamps', {
            'fields': ['received_at', 'processed_at', 'response_sent_at']
        }),
        ('Debug', {
            'fields': ['raw_payload'],
            'classes': ['collapse']
        }),
    ]


@admin.register(FiwanoConversation)
class FiwanoConversationAdmin(admin.ModelAdmin):
    list_display = ['channel_id', 'sender_id', 'message_count', 'first_message_at', 'last_message_at']
    list_filter = ['first_message_at', 'last_message_at']
    search_fields = ['channel_id', 'sender_id']
    readonly_fields = ['first_message_at', 'last_message_at', 'message_count', 'chat_history']
    
    fieldsets = [
        ('Conversation Info', {
            'fields': ['channel_id', 'sender_id']
        }),
        ('Stats', {
            'fields': ['message_count', 'first_message_at', 'last_message_at']
        }),
        ('History', {
            'fields': ['chat_history'],
            'classes': ['collapse']
        }),
    ]
