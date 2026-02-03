"""
MongoDB index creation script for chat collections.

Run this script to create all necessary indexes for optimal performance.
Usage: python manage.py shell < chat/migrations/create_indexes.py
"""
from pymongo import ASCENDING, DESCENDING, IndexModel
from chat.mongo_client import get_mongo_db
from chat.mongo_models import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION


def create_conversations_indexes():
    """Create indexes for conversations collection."""
    db = get_mongo_db()
    collection = db[CONVERSATIONS_COLLECTION]
    
    indexes = [
        # Index for finding user's conversations
        IndexModel(
            [('participants.user_id', ASCENDING)],
            name='idx_participants_user_id'
        ),
        
        # Index for sorting by last message (used in conversation lists)
        IndexModel(
            [('last_message_at', DESCENDING)],
            name='idx_last_message_at'
        ),
        
        # Compound index for user conversations sorted by activity
        IndexModel(
            [
                ('participants.user_id', ASCENDING),
                ('last_message_at', DESCENDING)
            ],
            name='idx_user_conversations'
        ),
        
        # Index for finding project conversations
        IndexModel(
            [('project_id', ASCENDING)],
            name='idx_project_id',
            sparse=True  # Only index documents with project_id
        ),
        
        # Index for finding startup conversations
        IndexModel(
            [('startup_id', ASCENDING)],
            name='idx_startup_id',
            sparse=True  # Only index documents with startup_id
        ),
        
        # Index for filtering by conversation type
        IndexModel(
            [('type', ASCENDING)],
            name='idx_type'
        ),
        
        # Compound index for project conversations sorted by activity
        IndexModel(
            [
                ('project_id', ASCENDING),
                ('last_message_at', DESCENDING)
            ],
            name='idx_project_conversations',
            sparse=True
        ),
    ]
    
    # Create all indexes
    result = collection.create_indexes(indexes)
    print(f"Created {len(result)} indexes for '{CONVERSATIONS_COLLECTION}' collection:")
    for index_name in result:
        print(f"  - {index_name}")
    
    return result


def create_messages_indexes():
    """Create indexes for messages collection."""
    db = get_mongo_db()
    collection = db[MESSAGES_COLLECTION]
    
    indexes = [
        # Primary index for fetching conversation messages
        IndexModel(
            [
                ('conversation_id', ASCENDING),
                ('created_at', DESCENDING)
            ],
            name='idx_conversation_messages'
        ),
        
        # Index for pagination queries
        IndexModel(
            [
                ('conversation_id', ASCENDING),
                ('_id', DESCENDING)
            ],
            name='idx_conversation_pagination'
        ),
        
        # Index for finding messages by sender
        IndexModel(
            [('sender_id', ASCENDING)],
            name='idx_sender_id'
        ),
        
        # Index for filtering unread messages
        IndexModel(
            [
                ('conversation_id', ASCENDING),
                ('read_by', ASCENDING),
                ('deleted', ASCENDING)
            ],
            name='idx_unread_messages'
        ),
        
        # Compound index for searching messages
        IndexModel(
            [
                ('conversation_id', ASCENDING),
                ('content', 'text')  # Text index for full-text search
            ],
            name='idx_message_search'
        ),
        
        # Optional: TTL index to auto-delete old messages (commented out by default)
        # Uncomment if you want messages to be automatically deleted after X days
        # IndexModel(
        #     [('created_at', ASCENDING)],
        #     name='idx_ttl_messages',
        #     expireAfterSeconds=7776000  # 90 days
        # ),
    ]
    
    # Create all indexes
    result = collection.create_indexes(indexes)
    print(f"Created {len(result)} indexes for '{MESSAGES_COLLECTION}' collection:")
    for index_name in result:
        print(f"  - {index_name}")
    
    return result


def list_existing_indexes():
    """List all existing indexes in chat collections."""
    db = get_mongo_db()
    
    print("\n=== Existing Indexes ===\n")
    
    # Conversations collection
    print(f"Collection: {CONVERSATIONS_COLLECTION}")
    conv_indexes = db[CONVERSATIONS_COLLECTION].list_indexes()
    for idx in conv_indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")
    
    print()
    
    # Messages collection
    print(f"Collection: {MESSAGES_COLLECTION}")
    msg_indexes = db[MESSAGES_COLLECTION].list_indexes()
    for idx in msg_indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")
    
    print()


def drop_all_indexes():
    """
    Drop all indexes except _id index.
    WARNING: Use with caution!
    """
    db = get_mongo_db()
    
    print("Dropping all non-_id indexes...")
    
    # Drop conversation indexes
    db[CONVERSATIONS_COLLECTION].drop_indexes()
    print(f"  - Dropped indexes from {CONVERSATIONS_COLLECTION}")
    
    # Drop message indexes
    db[MESSAGES_COLLECTION].drop_indexes()
    print(f"  - Dropped indexes from {MESSAGES_COLLECTION}")
    
    print("Done!\n")


if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("MongoDB Index Creation Script")
    print("=" * 60)
    print()
    
    # Check if user wants to drop existing indexes
    if '--drop' in sys.argv:
        confirm = input("Are you sure you want to drop all existing indexes? (yes/no): ")
        if confirm.lower() == 'yes':
            drop_all_indexes()
        else:
            print("Aborted.")
            sys.exit(0)
    
    # List existing indexes before creation
    if '--list' in sys.argv:
        list_existing_indexes()
        sys.exit(0)
    
    # Create indexes
    try:
        print("Creating indexes for conversations...")
        create_conversations_indexes()
        print()
        
        print("Creating indexes for messages...")
        create_messages_indexes()
        print()
        
        print("=" * 60)
        print("All indexes created successfully!")
        print("=" * 60)
        print()
        
        # List all indexes
        list_existing_indexes()
        
    except Exception as e:
        print(f"\nError creating indexes: {e}")
        sys.exit(1)
