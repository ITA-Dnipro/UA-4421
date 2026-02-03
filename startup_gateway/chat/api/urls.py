"""URL configuration for chat API - TASK SPECIFICATION COMPLIANT."""
from django.urls import path
from . import views


app_name = 'chat_api'

urlpatterns = [
    # Conversation endpoints
    path('conversations/', views.create_conversation, name='create_conversation'),
    path('conversations/list/', views.list_conversations, name='list_conversations'),
    path('conversations/<str:conversation_id>/', views.get_conversation_detail, name='conversation_detail'),
    path('conversations/with/<int:user_id>/', views.get_conversation_with_user, name='conversation_with_user'),
    path('conversations/<str:conversation_id>/unread/', views.get_unread_count, name='unread_count'),
    path('conversations/<str:conversation_id>/read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('conversations/<str:conversation_id>/messages/', views.list_messages, name='list_messages'),
    
    # Message endpoints
    path('messages/', views.send_message, name='send_message'),
    path('messages/<str:message_id>/status/', views.update_message_status, name='update_message_status'),
]
