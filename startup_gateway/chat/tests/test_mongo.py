"""Tests for MongoDB chat functionality - TASK SPECIFICATION COMPLIANT."""
import os
os.environ['MONGO_DB_NAME'] = 'startup_gateway_test'

from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.mongo_client import get_mongo_db
from chat.mongo_models import (
    Conversation, Message, Attachment,
    CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION,
    MessageStatus
)
from chat.mongo_service import get_chat_service

User = get_user_model()


class MongoDBConnectionTest(TestCase):
    """Test MongoDB connection."""
    
    def test_mongo_connection(self):
        """Test that we can connect to MongoDB."""
        db = get_mongo_db()
        # Ping the database
        result = db.client.admin.command('ping')
        self.assertEqual(result.get('ok'), 1.0)
    
    # def test_get_database(self):
    #     """Test that we can get the test database."""
    #     db = get_mongo_db()
    #     self.assertEqual(db.name, 'startup_gateway_test')


class MongoModelTest(TestCase):
    """Test MongoDB models and schemas."""
    
    def test_attachment_creation(self):
        """Test creating an Attachment."""
        attachment = Attachment(
            upload_id="upload_123",
            url="https://example.com/file.pdf",
            type="document",
            filename="document.pdf",
            size=1024
        )
        
        data = attachment.to_dict()
        self.assertEqual(data['upload_id'], "upload_123")
        self.assertEqual(data['url'], "https://example.com/file.pdf")
        self.assertEqual(data['type'], "document")
    
    def test_conversation_creation(self):
        """Test creating a Conversation with task-compliant schema."""
        conversation = Conversation(
            participants=[10, 20],  # Simple array of user IDs
            project_id=None,
            startup_id=None,
            meta={'test': 'data'}
        )
        
        data = conversation.to_dict()
        
        # Check UUID was generated
        self.assertIn('conversation_id', data)
        self.assertTrue(len(data['conversation_id']) > 0)
        
        # Check participants is simple array
        self.assertEqual(data['participants'], [10, 20])
        self.assertIsInstance(data['participants'], list)
        self.assertIsInstance(data['participants'][0], int)
        
        # Check optional fields
        self.assertIsNone(data.get('project_id'))
        self.assertIsNone(data.get('startup_id'))
        self.assertEqual(data['meta'], {'test': 'data'})
    
    def test_message_creation(self):
        """Test creating a Message with task-compliant schema."""
        message = Message(
            conversation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",  # UUID string
            sender_id=10,
            body="Hello!",  # "body" not "content"
            attachments=[],
            status=MessageStatus.SENT,
            meta={'test': 'data'}
        )
        
        data = message.to_dict()
        
        # Check fields
        self.assertEqual(data['conversation_id'], "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        self.assertEqual(data['sender_id'], 10)
        self.assertEqual(data['body'], "Hello!")  # body, not content
        self.assertEqual(data['status'], "sent")
        self.assertEqual(data['meta'], {'test': 'data'})


class ChatServiceTest(TestCase):
    """Test ChatService operations."""
    
    def setUp(self):
        """Set up test users and clean database."""
        # Clean test database
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        # Create test users with roles
        from users.models import Role
        
        # Create roles
        investor_role, _ = Role.objects.get_or_create(name='investor')
        startup_role, _ = Role.objects.get_or_create(name='startup')
        
        # Create investor user
        self.investor = User.objects.create_user(
            username='investor_test',
            email='investor@test.com',
            password='password123'
        )
        self.investor.roles.add(investor_role)
        
        # Create startup user
        self.startup = User.objects.create_user(
            username='startup_test',
            email='startup@test.com',
            password='password123'
        )
        self.startup.roles.add(startup_role)
        
        # Another startup for testing
        self.startup2 = User.objects.create_user(
            username='startup_test2',
            email='startup2@test.com',
            password='password123'
        )
        self.startup2.roles.add(startup_role)
        
        self.chat_service = get_chat_service()
    
    def tearDown(self):
        """Clean up after tests."""
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
    
    def test_create_conversation_by_investor(self):
        """Test that investor can create a conversation."""
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Check conversation was created
        self.assertIsNotNone(conversation_id)
        self.assertTrue(len(conversation_id) > 0)  # UUID string
        
        # Verify in database
        conversation = self.chat_service.get_conversation(conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(set(conversation['participants']), {self.investor.id, self.startup.id})
    
    def test_create_conversation_by_non_investor_fails(self):
        """Test that non-investor cannot create a conversation."""
        with self.assertRaises(PermissionError):
            self.chat_service.create_conversation(
                initiator_id=self.startup.id,  # Startup trying to initiate
                recipient_id=self.investor.id
            )
    
    def test_create_duplicate_conversation(self):
        """Test that duplicate conversations return existing conversation_id."""
        # Create first conversation
        conv_id_1 = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Try to create duplicate
        conv_id_2 = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Should return same conversation_id
        self.assertEqual(conv_id_1, conv_id_2)
    
    def test_get_conversation_between_users(self):
        """Test finding conversation between two users."""
        # Create conversation
        self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Find it
        conversation = self.chat_service.get_conversation_between_users(
            self.investor.id,
            self.startup.id
        )
        
        self.assertIsNotNone(conversation)
        self.assertIn(self.investor.id, conversation['participants'])
        self.assertIn(self.startup.id, conversation['participants'])
    
    def test_get_user_conversations(self):
        """Test getting all conversations for a user."""
        # Create multiple conversations
        self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup2.id
        )
        
        # Get investor's conversations
        conversations = self.chat_service.get_user_conversations(
            user_id=self.investor.id
        )
        
        self.assertEqual(len(conversations), 2)
    
    def test_send_message(self):
        """Test sending a message with 'body' field."""
        # Create conversation
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Send message
        message_id = self.chat_service.send_message(
            conversation_id=conversation_id,
            sender_id=self.investor.id,
            body="Hello! Interested in your startup.",  # "body" not "content"
            meta={'source': 'web'}
        )
        
        self.assertIsNotNone(message_id)
        
        # Verify message
        messages = self.chat_service.get_messages(conversation_id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['body'], "Hello! Interested in your startup.")
        self.assertEqual(messages[0]['sender_id'], self.investor.id)
        self.assertEqual(messages[0]['meta'], {'source': 'web'})
    
    def test_send_message_with_attachments(self):
        """Test sending a message with attachments (with upload_id)."""
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Send message with attachment
        message_id = self.chat_service.send_message(
            conversation_id=conversation_id,
            sender_id=self.investor.id,
            body="Check this document",
            attachments=[{
                'upload_id': 'upload_abc123',  # Required
                'url': 'https://example.com/doc.pdf',
                'type': 'document',
                'filename': 'pitch-deck.pdf',
                'size': 2048576
            }]
        )
        
        # Verify attachment
        messages = self.chat_service.get_messages(conversation_id)
        self.assertEqual(len(messages[0]['attachments']), 1)
        self.assertEqual(messages[0]['attachments'][0]['upload_id'], 'upload_abc123')
        self.assertEqual(messages[0]['attachments'][0]['type'], 'document')
    
    def test_update_message_status(self):
        """Test updating message status (sent → delivered → read)."""
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        message_id = self.chat_service.send_message(
            conversation_id=conversation_id,
            sender_id=self.investor.id,
            body="Test message"
        )
        
        # Update to delivered
        success = self.chat_service.update_message_status(message_id, MessageStatus.DELIVERED)
        self.assertTrue(success)
        
        # Update to read
        success = self.chat_service.update_message_status(message_id, MessageStatus.READ)
        self.assertTrue(success)
    
    def test_get_unread_count(self):
        """Test getting unread message count using status field."""
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Send 3 messages
        for i in range(3):
            self.chat_service.send_message(
                conversation_id=conversation_id,
                sender_id=self.investor.id,
                body=f"Message {i}"
            )
        
        # Get unread count for startup
        count = self.chat_service.get_unread_count(
            conversation_id=conversation_id,
            user_id=self.startup.id
        )
        
        self.assertEqual(count, 3)
    
    def test_mark_all_as_read(self):
        """Test marking all messages as read."""
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Send messages
        for i in range(3):
            self.chat_service.send_message(
                conversation_id=conversation_id,
                sender_id=self.investor.id,
                body=f"Message {i}"
            )
        
        # Mark all as read
        count = self.chat_service.mark_all_as_read(
            conversation_id=conversation_id,
            user_id=self.startup.id
        )
        
        self.assertEqual(count, 3)
        
        # Verify unread count is now 0
        unread = self.chat_service.get_unread_count(
            conversation_id=conversation_id,
            user_id=self.startup.id
        )
        self.assertEqual(unread, 0)
    
    def test_get_messages_pagination(self):
        """Test message pagination."""
        conversation_id = self.chat_service.create_conversation(
            initiator_id=self.investor.id,
            recipient_id=self.startup.id
        )
        
        # Send 10 messages
        for i in range(10):
            self.chat_service.send_message(
                conversation_id=conversation_id,
                sender_id=self.investor.id,
                body=f"Message {i}"
            )
        
        # Get first 5
        messages = self.chat_service.get_messages(
            conversation_id=conversation_id,
            limit=5
        )
        self.assertEqual(len(messages), 5)
        
        # Get next 5
        messages_2 = self.chat_service.get_messages(
            conversation_id=conversation_id,
            limit=5,
            skip=5
        )
        self.assertEqual(len(messages_2), 5)
