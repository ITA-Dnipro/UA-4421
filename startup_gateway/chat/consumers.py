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
        self.chat = get_chat_service()

    async def disconnect(self, close_code):
        for conversation_id in list(self.joined_conversations):
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
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'mark_read':
                await self.handle_read(data)
            elif message_type == 'ack':
                await self.handle_ack(data)
            else:
                await self.send_error(f'Unknown type: {message_type}')
        except Exception as e:
            await self.send_error(str(e))

    async def handle_join(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            await self.send_error('conversation_id required')
            return

        is_participant = await database_sync_to_async(self.chat.is_participant)(
            conversation_id=conversation_id,
            user_id=self.user.id
        )
        if not is_participant:
            await self.send_error('You are not a participant in this conversation')
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
            message = await database_sync_to_async(self.chat.create_message)(
                conversation_id=conversation_id,
                sender_id=self.user.id,
                body=body,
                attachments=data.get('attachments', [])
            )

            created_at = message.get('created_at')
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()

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
                        'created_at': created_at,
                    }
                }
            )
        except Exception as e:
            await self.send_error(str(e))

    async def handle_typing(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            await self.send_error('conversation_id required')
            return

        await self.channel_layer.group_send(
            f'conversation_{conversation_id}',
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'conversation_id': conversation_id,
            }
        )

    async def handle_read(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            await self.send_error('conversation_id required')
            return

        is_participant = await database_sync_to_async(self.chat.is_participant)(
            conversation_id=conversation_id,
            user_id=self.user.id
        )
        if not is_participant:
            await self.send_error('You are not a participant in this conversation')
            return

        try:
            count = await database_sync_to_async(self.chat.mark_messages_read)(
                conversation_id=conversation_id,
                user_id=self.user.id
            )

            await self.channel_layer.group_send(
                f'conversation_{conversation_id}',
                {
                    'type': 'read_receipt',
                    'user_id': self.user.id,
                    'conversation_id': conversation_id,
                    'count': count,
                }
            )
        except Exception as e:
            await self.send_error(str(e))

    async def handle_ack(self, data):
        """Handle message acknowledgement (delivered status)."""
        message_id = data.get('message_id')
        if not message_id:
            await self.send_error('message_id required')
            return

        is_participant = await database_sync_to_async(self.chat.is_message_participant)(
            message_id=message_id,
            user_id=self.user.id
        )
        if not is_participant:
            await self.send_error('You are not a participant in this conversation')
            return

        try:
            updated = await database_sync_to_async(self.chat.mark_message_delivered)(
                message_id=message_id,
                user_id=self.user.id
            )

            if updated:
                conversation_id = updated.get('conversation_id')
                await self.channel_layer.group_send(
                    f'conversation_{conversation_id}',
                    {
                        'type': 'delivered_receipt',
                        'message_id': message_id,
                        'user_id': self.user.id,
                        'conversation_id': conversation_id,
                    }
                )
        except Exception as e:
            await self.send_error(str(e))

    async def message_received(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_received',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'conversation_id': event['conversation_id'],
            }))

    async def read_receipt(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'user_id': event['user_id'],
                'conversation_id': event['conversation_id'],
                'count': event.get('count', 0),
            }))

    async def delivered_receipt(self, event):
        """Broadcast delivered status to other participants."""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'delivered',
                'message_id': event['message_id'],
                'user_id': event['user_id'],
                'conversation_id': event['conversation_id'],
            }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))