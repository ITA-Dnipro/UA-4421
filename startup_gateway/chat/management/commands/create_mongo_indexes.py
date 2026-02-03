"""Django management command to create MongoDB indexes - TASK COMPLIANT."""
from django.core.management.base import BaseCommand
from chat.mongo_client import get_mongo_db
from chat.mongo_models import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION


class Command(BaseCommand):
    help = 'Create MongoDB indexes for chat collections - Task Specification Compliant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--drop',
            action='store_true',
            help='Drop existing indexes before creating new ones',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all existing indexes',
        )

    def handle(self, *args, **options):
        db = get_mongo_db()
        conversations = db[CONVERSATIONS_COLLECTION]
        messages = db[MESSAGES_COLLECTION]

        if options['list']:
            self.list_indexes(conversations, messages)
            return

        if options['drop']:
            self.stdout.write('Dropping existing indexes...')
            conversations.drop_indexes()
            messages.drop_indexes()
            self.stdout.write(self.style.SUCCESS('✓ Indexes dropped'))

        # Create indexes for conversations
        self.stdout.write('\nCreating indexes for conversations...')
        
        # Index on participants (simple array now)
        conversations.create_index('participants')
        self.stdout.write('  ✓ idx_participants')
        
        # Index on last_message_at for sorting
        conversations.create_index([('last_message_at', -1)])
        self.stdout.write('  ✓ idx_last_message_at')
        
        # Compound index for user conversations with sorting
        conversations.create_index([
            ('participants', 1),
            ('last_message_at', -1)
        ])
        self.stdout.write('  ✓ idx_user_conversations')
        
        # Unique index on conversation_id (UUID)
        conversations.create_index('conversation_id', unique=True)
        self.stdout.write('  ✓ idx_conversation_id (unique)')
        
        # Optional indexes for future use
        conversations.create_index('project_id', sparse=True)
        self.stdout.write('  ✓ idx_project_id (sparse)')
        
        conversations.create_index('startup_id', sparse=True)
        self.stdout.write('  ✓ idx_startup_id (sparse)')

        # Create indexes for messages
        self.stdout.write('\nCreating indexes for messages...')
        
        # Compound index for conversation messages with sorting
        messages.create_index([
            ('conversation_id', 1),
            ('created_at', -1)
        ])
        self.stdout.write('  ✓ idx_conversation_messages')
        
        # Index for pagination (conversation + _id for cursor-based)
        messages.create_index([
            ('conversation_id', 1),
            ('_id', -1)
        ])
        self.stdout.write('  ✓ idx_conversation_pagination')
        
        # Index on sender_id
        messages.create_index('sender_id')
        self.stdout.write('  ✓ idx_sender_id')
        
        # Index for unread messages (conversation + status)
        messages.create_index([
            ('conversation_id', 1),
            ('status', 1)
        ])
        self.stdout.write('  ✓ idx_unread_messages')

        self.stdout.write(self.style.SUCCESS('\n✅ All indexes created successfully!'))
        
        # Show current indexes
        self.stdout.write('\nCurrent Indexes:')
        self.list_indexes(conversations, messages)

    def list_indexes(self, conversations, messages):
        """List all indexes for both collections."""
        self.stdout.write('\nCollection: conversations')
        for idx in conversations.list_indexes():
            self.stdout.write(f"  - {idx['name']}: {idx['key']}")
        
        self.stdout.write('\nCollection: messages')
        for idx in messages.list_indexes():
            self.stdout.write(f"  - {idx['name']}: {idx['key']}")
