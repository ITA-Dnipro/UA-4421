import os
os.environ['MONGO_DB_NAME'] = 'startup_gateway_test'

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from chat.mongo_client import get_mongo_db
from chat.mongo_models import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION
from chat.mongo_service import get_chat_service

User = get_user_model()


class ConversationListAPITest(TestCase):
    
    def setUp(self):
        """Set up test data."""
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='pass123'
        )
        
        self.chat_service = get_chat_service()
        
        self.conv1 = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        self.conv2 = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user3.id]
        )

        self.conv3 = self.chat_service.create_conversation(
            participants=[self.user2.id, self.user3.id]
        )
        

        self.chat_service.create_message(
            conversation_id=self.conv1,
            sender_id=self.user2.id,
            body="Message in conv1"
        )
        self.chat_service.create_message(
            conversation_id=self.conv2,
            sender_id=self.user3.id,
            body="Unread message"
        )
    
    def test_list_conversations_authenticated(self):

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/conversations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # user1 has 2 conversations
        
        for item in response.data:
            self.assertIn('conversation', item)
            self.assertIn('last_message', item)
            self.assertIn('unread_count', item)
    
    def test_list_conversations_unauthenticated(self):
        response = self.client.get('/api/conversations/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_list_conversations_pagination(self):

        self.client.force_authenticate(user=self.user1)
        
        for i in range(5):
            conv_id = self.chat_service.create_conversation(
                participants=[self.user1.id, self.user2.id]
            )
            self.chat_service.create_message(
                conversation_id=conv_id,
                sender_id=self.user2.id,
                body=f"Message {i}"
            )
        
        response = self.client.get('/api/conversations/?page=1&page_size=3')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        response = self.client.get('/api/conversations/?page=2&page_size=3')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
    
    def test_list_shows_only_user_conversations(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/conversations/')
        
        conv_ids = [item['conversation']['conversation_id'] for item in response.data]
        
        self.assertIn(self.conv1, conv_ids)
        self.assertIn(self.conv2, conv_ids)
        self.assertNotIn(self.conv3, conv_ids)  


class ConversationCreateAPITest(TestCase):
    
    def setUp(self):
        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123'
        )
        
        self.chat_service = get_chat_service()
    
    def test_create_conversation_success(self):
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'participants': [self.user1.id, self.user2.id]
        }
        
        response = self.client.post('/api/conversations/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('conversation_id', response.data)
        
        result = self.chat_service.get_conversation(response.data['conversation_id'])
        self.assertIsNotNone(result)
    
    def test_create_conversation_with_project(self):
        self.client.force_authenticate(user=self.user1)
        
        import uuid
        project_id = str(uuid.uuid4()) 
        
        data = {
            'participants': [self.user1.id, self.user2.id],
            'project_id': project_id
        }
        
        response = self.client.post('/api/conversations/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        result = self.chat_service.get_conversation(response.data['conversation_id'])
        self.assertEqual(result['conversation']['project_id'], project_id)
    
    def test_create_conversation_unauthenticated(self):
        data = {
            'participants': [self.user1.id, self.user2.id]
        }
        
        response = self.client.post('/api/conversations/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_create_conversation_invalid_data(self):
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post('/api/conversations/', {'participants': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response = self.client.post('/api/conversations/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_conversation_rate_limit(self):
        self.client.force_authenticate(user=self.user1)

        data = {'participants': [self.user1.id, self.user2.id]}
        
        for _ in range(5):
            response = self.client.post('/api/conversations/', data, format='json')

            self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_429_TOO_MANY_REQUESTS])


class ConversationMessagesAPITest(TestCase):
    
    def setUp(self):

        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123'
        )
        
        self.chat_service = get_chat_service()
        
        self.conv_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        for i in range(10):
            self.chat_service.create_message(
                conversation_id=self.conv_id,
                sender_id=self.user1.id if i % 2 == 0 else self.user2.id,
                body=f"Message {i+1}"
            )
    
    def test_list_messages_success(self):

        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(f'/api/conversations/{self.conv_id}/messages/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('messages', response.data)
        self.assertIn('conversation', response.data)
    
    def test_list_messages_pagination(self):

        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(
            f'/api/conversations/{self.conv_id}/messages/?page=1&page_size=5'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['messages']), 5)
    
    def test_list_messages_unauthorized_user(self):

        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='pass123'
        )
        self.client.force_authenticate(user=user3)
        
        response = self.client.get(f'/api/conversations/{self.conv_id}/messages/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_list_messages_invalid_conversation(self):

        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/conversations/invalid-id/messages/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MessageCreateAPITest(TestCase):
    
    def setUp(self):

        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123'
        )
        
        self.chat_service = get_chat_service()
        
        self.conv_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
    
    def test_send_message_success(self):

        self.client.force_authenticate(user=self.user1)
        
        data = {
            'body': 'Test message via REST API'
        }
        
        response = self.client.post(
            f'/api/conversations/{self.conv_id}/messages/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message_id', response.data)
        

        result = self.chat_service.get_conversation(self.conv_id)
        messages = result['messages']
        self.assertTrue(any(msg['body'] == 'Test message via REST API' for msg in messages))
    
    def test_send_message_with_attachments(self):

        self.client.force_authenticate(user=self.user1)
        
        data = {
            'body': 'Message with attachment',
            'attachments': [
                {
                    'upload_id': 'test-upload-123',
                    'url': 'https://example.com/file.pdf',
                    'type': 'document'
                }
            ]
        }
        
        response = self.client.post(
            f'/api/conversations/{self.conv_id}/messages/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_send_message_unauthorized_user(self):

        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='pass123'
        )
        self.client.force_authenticate(user=user3)
        
        data = {'body': 'Unauthorized message'}
        
        response = self.client.post(
            f'/api/conversations/{self.conv_id}/messages/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_send_message_invalid_data(self):

        self.client.force_authenticate(user=self.user1)
        

        response = self.client.post(
            f'/api/conversations/{self.conv_id}/messages/',
            {'body': ''},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response = self.client.post(
            f'/api/conversations/{self.conv_id}/messages/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_send_message_updates_last_message_at(self):

        self.client.force_authenticate(user=self.user1)
        
        conv_before = self.chat_service.get_conversation(self.conv_id)
        last_message_before = conv_before['conversation'].get('last_message_at')
        
        import time
        time.sleep(0.1)  
        
        data = {'body': 'Test update timestamp'}
        response = self.client.post(
            f'/api/conversations/{self.conv_id}/messages/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        conv_after = self.chat_service.get_conversation(self.conv_id)
        last_message_after = conv_after['conversation']['last_message_at']
        
        self.assertIsNotNone(last_message_after)
        if last_message_before:
            self.assertNotEqual(last_message_before, last_message_after)


class MarkReadAPITest(TestCase):
    
    def setUp(self):

        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123'
        )
        
        self.chat_service = get_chat_service()
        
        self.conv_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        for i in range(5):
            self.chat_service.create_message(
                conversation_id=self.conv_id,
                sender_id=self.user2.id,
                body=f"Unread message {i+1}"
            )
    
    def test_mark_read_success(self):

        self.client.force_authenticate(user=self.user1)
        
        unread_before = self.chat_service.get_unread_count(self.conv_id, self.user1.id)
        self.assertEqual(unread_before, 5)
        
        response = self.client.post(f'/api/conversations/{self.conv_id}/read/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        unread_after = self.chat_service.get_unread_count(self.conv_id, self.user1.id)
        self.assertEqual(unread_after, 0)
    
    def test_mark_read_unauthorized_user(self):

        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='pass123'
        )
        self.client.force_authenticate(user=user3)
        
        response = self.client.post(f'/api/conversations/{self.conv_id}/read/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_mark_read_invalid_conversation(self):

        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post('/api/conversations/invalid-id/read/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_mark_read_idempotent(self):

        self.client.force_authenticate(user=self.user1)
        
        response1 = self.client.post(f'/api/conversations/{self.conv_id}/read/')
        self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)
        
        response2 = self.client.post(f'/api/conversations/{self.conv_id}/read/')
        self.assertEqual(response2.status_code, status.HTTP_204_NO_CONTENT)
        
        unread = self.chat_service.get_unread_count(self.conv_id, self.user1.id)
        self.assertEqual(unread, 0)


class OpenAPIDocumentationTest(TestCase):
    
    def setUp(self):

        self.client = APIClient()
    
    def test_openapi_schema_exists(self):

        response = self.client.get('/api/schema/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        content = response.content.decode('utf-8')
        self.assertIn('conversations', content.lower())
        self.assertIn('messages', content.lower())


class EdgeCasesAndSecurityTest(TestCase):
    
    def setUp(self):

        db = get_mongo_db()
        db[CONVERSATIONS_COLLECTION].delete_many({})
        db[MESSAGES_COLLECTION].delete_many({})
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123'
        )
        
        self.chat_service = get_chat_service()
    
    def test_sql_injection_protection(self):

        self.client.force_authenticate(user=self.user1)
        
        malicious_id = "'; DROP TABLE users; --"
        
        response = self.client.get(f'/api/conversations/{malicious_id}/messages/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_xss_in_message_body(self):
  
        self.client.force_authenticate(user=self.user1)
        
        conv_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        xss_payload = '<script>alert("XSS")</script>'
        
        data = {'body': xss_payload}
        response = self.client.post(
            f'/api/conversations/{conv_id}/messages/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        result = self.chat_service.get_conversation(conv_id)
        stored_body = result['messages'][0]['body']
        self.assertEqual(stored_body, xss_payload)
    
    def test_extremely_long_message(self):

        self.client.force_authenticate(user=self.user1)
        
        conv_id = self.chat_service.create_conversation(
            participants=[self.user1.id, self.user2.id]
        )
        
        long_body = 'a' * 6000
        
        data = {'body': long_body}
        response = self.client.post(
            f'/api/conversations/{conv_id}/messages/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_negative_pagination_values(self):

        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/conversations/?page=-1&page_size=-10')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_pagination_page_size_limit(self):

        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/conversations/?page=1&page_size=200')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)