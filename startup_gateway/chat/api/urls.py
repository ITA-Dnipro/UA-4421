from django.urls import path
from .views import (
    ConversationAPIView,
    ConversationMessagesAPIView,
    MarkReadAPIView,
)

app_name = 'chat'

urlpatterns = [
    path(
        "conversations/",
        ConversationAPIView.as_view(),
        name="conversations"
    ),
    
    path(
        "conversations/<str:conversation_id>/messages/",
        ConversationMessagesAPIView.as_view(),
        name="conversation-messages"
    ),
    
    path(
        "conversations/<str:conversation_id>/read/",
        MarkReadAPIView.as_view(),
        name="conversation-read"
    ),
]