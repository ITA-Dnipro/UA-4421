"""WebSocket Consumer tests"""
import asyncio
from django.test import TestCase, override_settings
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async

from chat.consumers import ChatConsumer
from chat.mongo_service import get_chat_service
from users.models import User


TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class ChatConsumerTest(TestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
    
    async def test_authentication_required(self):
        """Test that unauthenticated users cannot connect."""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            "/ws/chat/"
        )
        communicator.scope['user'] = None
        
        connected, _ = await communicator.connect()
        
        self.assertFalse(connected)
    
    async def test_join_and_leave_conversation(self):
        """Test joining and leaving a conversation."""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            "/ws/chat/"
        )
        communicator.scope['user'] = self.user1
        
        await communicator.connect()
        
        await communicator.send_json_to({
            'type': 'join_conversation',
            'conversation_id': 'test-123'
        })
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'joined')
        
        await communicator.send_json_to({
            'type': 'leave_conversation',
            'conversation_id': 'test-123'
        })
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'left')
        
        await communicator.disconnect()
    
    async def test_send_message_persists_and_broadcasts(self):
        """Test that sent message is saved to MongoDB and broadcast to all participants."""
        comm1 = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        comm1.scope['user'] = self.user1
        
        comm2 = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        comm2.scope['user'] = self.user2
        
        await comm1.connect()
        await comm2.connect()
        
        chat = get_chat_service()
        conversation_id = await database_sync_to_async(chat.create_conversation)(
            participants=[self.user1.id, self.user2.id],
            meta={'test': True}
        )
        
        await comm1.send_json_to({'type': 'join_conversation', 'conversation_id': conversation_id})
        await comm2.send_json_to({'type': 'join_conversation', 'conversation_id': conversation_id})
        await comm1.receive_json_from()
        await comm2.receive_json_from()
        
        await asyncio.sleep(0.1)
        
        await comm1.send_json_to({
            'type': 'send_message',
            'conversation_id': conversation_id,
            'body': 'Test message'
        })
        
        await asyncio.sleep(0.2)
        
        msg1 = await comm1.receive_json_from(timeout=5)
        msg2 = await comm2.receive_json_from(timeout=5)
        
        self.assertEqual(msg1['type'], 'message_received')
        self.assertEqual(msg2['type'], 'message_received')
        self.assertEqual(msg1['message']['body'], 'Test message')
        self.assertEqual(msg2['message']['body'], 'Test message')
        
        result = await database_sync_to_async(chat.get_conversation)(conversation_id)
        messages = result['messages']
        self.assertTrue(any(m['body'] == 'Test message' for m in messages))
        
        await comm1.disconnect()
        await comm2.disconnect()