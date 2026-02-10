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

        self.stdout.write('\nCreating required indexes (task-compliant)...')
        
        conversations.create_index('participants')
        self.stdout.write('  ✓ idx_participants')
        
        conversations.create_index([('last_message_at', -1)])
        self.stdout.write('  ✓ idx_last_message_at_desc')

        messages.create_index([
            ('conversation_id', 1),
            ('created_at', -1)
        ])
        self.stdout.write('  ✓ idx_conversation_created_at_desc')

        self.stdout.write(self.style.SUCCESS('\n✅ Task-compliant indexes created successfully!'))
        
        self.stdout.write('\nCurrent Indexes:')
        self.list_indexes(conversations, messages)

    def list_indexes(self, conversations, messages):
        self.stdout.write('\nCollection: conversations')
        for idx in conversations.list_indexes():
            self.stdout.write(f"  - {idx['name']}: {idx['key']}")
        
        self.stdout.write('\nCollection: messages')
        for idx in messages.list_indexes():
            self.stdout.write(f"  - {idx['name']}: {idx['key']}")
