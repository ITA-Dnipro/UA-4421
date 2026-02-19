"""
WebSocket URL routing for chat application.

Maps WebSocket paths to consumers (like urls.py for HTTP).
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # ws://localhost:8000/ws/chat/
    path('ws/chat/', consumers.ChatConsumer.as_asgi()),
]