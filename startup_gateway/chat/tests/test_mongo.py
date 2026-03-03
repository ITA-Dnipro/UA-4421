"""Minimal tests for MongoDB chat - only acceptance criteria."""
import os
os.environ['MONGO_DB_NAME'] = 'startup_gateway_test'

from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.mongo_client import get_mongo_db
from chat.mongo_models import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION
from chat.mongo_service import get_chat_service

User = get_user_model()


class MongoDBChatTest(TestCase):
    """
    Minimal tests for acceptance criteria:
    - Unit tests that connect to test Mongo instance
    - Create a conversation
    - Create a message
    """

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

        self.chat_service = get_chat_service()

    def tearDown(self):
        """Clean up after tests."""
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})

    def test_create_conversation(self):
        """
        Acceptance criteria: Unit test that creates a conversation.

        Tests that we can:
        - Connect to test MongoDB instance
        - Create a conversation document
        - Verify it's stored correctly
        """
        conversation_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )

        self.assertIsNotNone(conversation_id)
        self.assertTrue(len(conversation_id) > 0)

        result = self.chat_service.get_conversation(conversation_id)
        self.assertIsNotNone(result)

        conversation = result['conversation']

        self.assertEqual(set(conversation['participants']), {self.user1.id, self.user2.id})

        self.assertIn('conversation_id', conversation)
        self.assertIn('participants', conversation)
        self.assertIn('created_at', conversation)
        self.assertIsNone(conversation.get('project_id'))
        self.assertIsNone(conversation.get('startup_id'))

    def test_create_message(self):
        """
        Acceptance criteria: Unit test that creates a message.

        Tests that we can:
        - Create a message in a conversation
        - Verify message document structure
        - Verify message is stored correctly
        """
        conversation_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )

        message = self.chat_service.create_message(
            conversation_id=conversation_id,
            sender_id=self.user1.id,
            body="Test message"
        )

        self.assertIsNotNone(message)
        self.assertIn('_id', message)
        self.assertIsNotNone(message['_id'])

        self.assertEqual(message['conversation_id'], conversation_id)
        self.assertEqual(message['sender_id'], self.user1.id)
        self.assertEqual(message['body'], "Test message")
        self.assertEqual(message['status'], 'sent')
        self.assertIn('created_at', message)
        self.assertIn('meta', message)
        self.assertEqual(message['attachments'], [])