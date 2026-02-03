"""Django admin configuration for chat app.

Note: MongoDB collections don't use Django ORM models, so this provides
basic statistics and management tools through custom admin views.
"""
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse

from .mongo_service import get_chat_service
from .mongo_client import get_mongo_db
from .mongo_models import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION


class ChatAdminSite(admin.AdminSite):
    """Custom admin site for Chat app."""
    
    def get_urls(self):
        """Add custom admin URLs."""
        urls = super().get_urls()
        custom_urls = [
            path('chat-stats/', self.admin_view(self.chat_stats_view), name='chat_stats'),
            path('chat-indexes/', self.admin_view(self.chat_indexes_view), name='chat_indexes'),
        ]
        return custom_urls + urls
    
    def chat_stats_view(self, request):
        """View for displaying chat statistics."""
        db = get_mongo_db()
        
        stats = {
            'conversations': {
                'total': db[CONVERSATIONS_COLLECTION].count_documents({}),
                'by_type': {},
            },
            'messages': {
                'total': db[MESSAGES_COLLECTION].count_documents({}),
                'total_deleted': db[MESSAGES_COLLECTION].count_documents({'deleted': True}),
            },
        }
        
        # Count conversations by type
        pipeline = [
            {'$group': {'_id': '$type', 'count': {'$sum': 1}}}
        ]
        for doc in db[CONVERSATIONS_COLLECTION].aggregate(pipeline):
            stats['conversations']['by_type'][doc['_id']] = doc['count']
        
        context = {
            'title': 'Chat Statistics',
            'stats': stats,
        }
        
        return render(request, 'admin/chat_stats.html', context)
    
    def chat_indexes_view(self, request):
        """View for displaying MongoDB indexes."""
        db = get_mongo_db()
        
        conversations_indexes = list(db[CONVERSATIONS_COLLECTION].list_indexes())
        messages_indexes = list(db[MESSAGES_COLLECTION].list_indexes())
        
        context = {
            'title': 'MongoDB Indexes',
            'conversations_indexes': conversations_indexes,
            'messages_indexes': messages_indexes,
        }
        
        return render(request, 'admin/chat_indexes.html', context)


# Note: Since we're using MongoDB, we don't have traditional Django models to register.
# Instead, you can access chat statistics and management through:
# /admin/chat-stats/ and /admin/chat-indexes/

# If you want to add links to these in the admin index, you can use AdminSite.index_template
# or add them through custom admin templates.
