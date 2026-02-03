"""Django app configuration for chat."""
from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Chat'
    
    def ready(self):
        """Initialize MongoDB connection when app is ready."""
        from .mongo_client import get_mongo_client
        # Test connection on startup
        try:
            client = get_mongo_client()
            # Ping to verify connection
            client.admin.command('ping')
        except Exception as e:
            # Log warning but don't prevent app from starting
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"MongoDB connection failed on startup: {e}")
