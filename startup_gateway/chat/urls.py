"""URL configuration for chat application."""
from django.urls import path, include


app_name = 'chat'

urlpatterns = [
    path('api/', include('chat.api.urls')),
]
