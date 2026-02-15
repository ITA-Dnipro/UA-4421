"""service layer tests """
import os
os.environ['MONGO_DB_NAME'] = 'startup_gateway_test'

from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.mongo_client import get_mongo_db
from chat.mongo_models import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION
from chat.mongo_service import get_chat_service

User = get_user_model()


class ServiceLayerTests(TestCase):
    """Tests for Task 9 service layer functions."""
    
    def setUp(self):
        """Set up test users and clean database."""
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='password123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='password123'
        )
        
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='password123'
        )
        
        self.chat_service = get_chat_service()
    
    def tearDown(self):
        """Clean up after tests."""
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
    
    def test_create_message(self):
        """
        Test create_message: validates participants, creates conversation
        if not exists, updates last_message_at, persists to Mongo.
        """
        import uuid
        
        conversation_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        message = self.chat_service.create_message(
            conversation_id=conversation_id,
            sender_id=self.user1.id,
            body="Test message"
        )
        
        self.assertIsNotNone(message)
        self.assertEqual(message['sender_id'], self.user1.id)
        self.assertEqual(message['body'], "Test message")
        
        with self.assertRaises(ValueError):
            self.chat_service.create_message(
                conversation_id=conversation_id,
                sender_id=self.user3.id,
                body="Unauthorized"
            )
        
        new_conv_id = str(uuid.uuid4())
        message2 = self.chat_service.create_message(
            conversation_id=new_conv_id,
            sender_id=self.user1.id,
            body="First message creates conversation"
        )
        
        result = self.chat_service.get_conversation(new_conv_id)
        self.assertIsNotNone(result)
        self.assertIn(self.user1.id, result['conversation']['participants'])
        self.assertIsNotNone(result['conversation']['last_message_at'])
    
    def test_get_conversation(self):
        """Test get_conversation with pagination."""
        conversation_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        for i in range(10):
            self.chat_service.create_message(
                conversation_id=conversation_id,
                sender_id=self.user1.id,
                body=f"Message {i+1}"
            )
        
        result = self.chat_service.get_conversation(
            conversation_id=conversation_id,
            page=1,
            page_size=5
        )
        
        self.assertIn('conversation', result)
        self.assertIn('messages', result)
        self.assertIn('has_next', result)
        self.assertIn('page', result)
        self.assertIn('page_size', result)
        self.assertIn('total', result)
        
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 5)
        self.assertEqual(result['total'], 10)
        self.assertEqual(len(result['messages']), 5)
        self.assertTrue(result['has_next'])
        
        result2 = self.chat_service.get_conversation(
            conversation_id=conversation_id,
            page=2,
            page_size=5
        )
        
        self.assertEqual(len(result2['messages']), 5)
        self.assertFalse(result2['has_next'])
    
    def test_list_conversations_for_user(self):
        """Test list_conversations_for_user with last_message and unread_count."""
        conv1_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        conv2_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user3.id]
        )
        
        conv3_id = self.chat_service.create_conversation(
            participants=[self.user2.id, self.user3.id]
        )
        
        self.chat_service.create_message(
            conversation_id=conv1_id,
            sender_id=self.user1.id,
            body="Message in conv1"
        )
        
        for i in range(3):
            self.chat_service.create_message(
                conversation_id=conv2_id,
                sender_id=self.user3.id,
                body=f"Unread message {i+1}"
            )
        
        conversations = self.chat_service.list_conversations_for_user(
            user_id=self.user1.id,
            page=1,
            page_size=10
        )
        
        self.assertEqual(len(conversations), 2)
        
        for item in conversations:
            self.assertIn('conversation', item)
            self.assertIn('last_message', item)
            self.assertIn('unread_count', item)
            self.assertIn(self.user1.id, item['conversation']['participants'])
        
        conv2_item = [c for c in conversations if c['conversation']['conversation_id'] == conv2_id][0]
        self.assertEqual(conv2_item['unread_count'], 3)
        
        conv1_item = [c for c in conversations if c['conversation']['conversation_id'] == conv1_id][0]
        self.assertEqual(conv1_item['unread_count'], 0)
    
    def test_mark_messages_read(self):
        """Test mark_messages_read."""
        conversation_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        for i in range(5):
            self.chat_service.create_message(
                conversation_id=conversation_id,
                sender_id=self.user2.id,
                body=f"Message {i+1}"
            )
        
        for i in range(2):
            self.chat_service.create_message(
                conversation_id=conversation_id,
                sender_id=self.user1.id,
                body=f"My message {i+1}"
            )
        
        unread_before = self.chat_service.get_unread_count(
            conversation_id=conversation_id,
            user_id=self.user1.id
        )
        self.assertEqual(unread_before, 5)
        
        marked_count = self.chat_service.mark_messages_read(
            conversation_id=conversation_id,
            user_id=self.user1.id
        )
        
        self.assertEqual(marked_count, 5)
        
        unread_after = self.chat_service.get_unread_count(
            conversation_id=conversation_id,
            user_id=self.user1.id
        )
        self.assertEqual(unread_after, 0)