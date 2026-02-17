"""WebSocket consumer for real-time chat."""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from chat.mongo_service import get_chat_service


class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        await self.accept()
        self.joined_conversations = set()
    
    async def disconnect(self, close_code):
        for conversation_id in self.joined_conversations:
            await self.channel_layer.group_discard(
                f'conversation_{conversation_id}',
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'join_conversation':
                await self.handle_join(data)
            elif message_type == 'leave_conversation':
                await self.handle_leave(data)
            elif message_type == 'send_message':
                await self.handle_send(data)
            else:
                await self.send_error(f'Unknown type: {message_type}')
        except Exception as e:
            await self.send_error(str(e))
    
    async def handle_join(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            await self.send_error('conversation_id required')
            return
        
        await self.channel_layer.group_add(
            f'conversation_{conversation_id}',
            self.channel_name
        )
        
        self.joined_conversations.add(conversation_id)
        
        await self.send(text_data=json.dumps({
            'type': 'joined',
            'conversation_id': conversation_id
        }))
    
    async def handle_leave(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            await self.send_error('conversation_id required')
            return
        
        await self.channel_layer.group_discard(
            f'conversation_{conversation_id}',
            self.channel_name
        )
        
        self.joined_conversations.discard(conversation_id)
        
        await self.send(text_data=json.dumps({
            'type': 'left',
            'conversation_id': conversation_id
        }))
    
    async def handle_send(self, data):
        conversation_id = data.get('conversation_id')
        body = data.get('body')
        
        if not conversation_id or not body:
            await self.send_error('conversation_id and body required')
            return
        
        try:
            chat = get_chat_service()
            message = await database_sync_to_async(chat.create_message)(
                conversation_id=conversation_id,
                sender_id=self.user.id,
                body=body,
                attachments=data.get('attachments', [])
            )
            
            await self.channel_layer.group_send(
                f'conversation_{conversation_id}',
                {
                    'type': 'message_received',
                    'message': {
                        'message_id': str(message['_id']),
                        'conversation_id': conversation_id,
                        'sender_id': self.user.id,
                        'body': body,
                        'attachments': message.get('attachments', []),
                        'status': message['status'],
                        'created_at': message['created_at'],
                    }
                }
            )
        except Exception as e:
            await self.send_error(str(e))

    async def message_received(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_received',
            'message': event['message']
        }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))