"""Django app configuration for chat."""
from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Chat application configuration."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Chat'
    
    # Connection is lazy - only created when first needed
    # No need to check MongoDB in ready() - it breaks migrations, tests, etc.