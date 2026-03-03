"""Service layer for MongoDB chat operations.

Implements server-side conversation/message service with:
- Message persistence with conversation auto-creation
- Pagination for messages and conversations
- Unread count tracking
- Mark as read functionality
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from pymongo.errors import PyMongoError

from .mongo_client import get_mongo_db
from .mongo_models import (
    Conversation, Message, Attachment,
    CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION,
    MessageStatus
)


class ChatService:
    """Service for managing conversations and messages in MongoDB."""
    
    def __init__(self):
        """Initialize with MongoDB database connection."""
        self.db = get_mongo_db()
        self.conversations = self.db[CONVERSATIONS_COLLECTION]
        self.messages = self.db[MESSAGES_COLLECTION]
    
    def create_conversation(
        self,
        participants: List[int],
        project_id: Optional[str] = None,
        startup_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> str:
        if project_id is not None and not isinstance(project_id, str):
            project_id = str(project_id)
        if startup_id is not None and not isinstance(startup_id, str):
            startup_id = str(startup_id)

        conversation = Conversation(
            participants=participants,
            project_id=project_id,
            startup_id=startup_id,
            meta=meta or {}
        )
        
        self.conversations.insert_one(conversation.to_dict())
        return conversation.conversation_id
    
    def create_message(
        self,
        conversation_id: str,
        sender_id: int,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        conversation = self.conversations.find_one({'conversation_id': conversation_id})
        
        if not conversation:
            new_conversation = Conversation(
                conversation_id=conversation_id,
                participants=[sender_id],
                meta=meta or {}
            )
            self.conversations.insert_one(new_conversation.to_dict())
            conversation = self.conversations.find_one({'conversation_id': conversation_id})
        
        if sender_id not in conversation['participants']:
            raise ValueError(f"User {sender_id} is not a participant in this conversation")
        
        attachment_objects = []
        if attachments:
            for att in attachments:
                attachment_objects.append(Attachment(**att))
        
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            body=body,
            attachments=attachment_objects,
            meta=meta or {}
        )
        
        result = self.messages.insert_one(message.to_dict())
        
        self.conversations.update_one(
            {'conversation_id': conversation_id},
            {'$set': {'last_message_at': datetime.utcnow().isoformat()}}
        )
        
        message_doc = message.to_dict()
        message_doc['_id'] = str(result.inserted_id)
        return message_doc
    
    def get_conversation(
        self,
        conversation_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        try:
            conversation = self.conversations.find_one({'conversation_id': conversation_id})
            if not conversation:
                return None
            
            conversation['_id'] = str(conversation['_id'])
            
            skip = (page - 1) * page_size
            total = self.messages.count_documents({'conversation_id': conversation_id})
            
            cursor = self.messages.find({'conversation_id': conversation_id})\
                .sort('created_at', 1)\
                .skip(skip)\
                .limit(page_size + 1)
            
            messages = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                messages.append(doc)
            
            has_next = len(messages) > page_size
            if has_next:
                messages = messages[:page_size]
            
            return {
                'conversation': conversation,
                'messages': messages,
                'has_next': has_next,
                'page': page,
                'page_size': page_size,
                'total': total
            }
            
        except PyMongoError:
            return None
    
    def list_conversations_for_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        skip = (page - 1) * page_size
        
        cursor = self.conversations.find({'participants': user_id})\
            .sort('last_message_at', -1)\
            .skip(skip)\
            .limit(page_size)
        
        results = []
        for conv in cursor:
            conv['_id'] = str(conv['_id'])
            
            last_message = self.messages.find_one(
                {'conversation_id': conv['conversation_id']},
                sort=[('created_at', -1)]
            )
            if last_message:
                last_message['_id'] = str(last_message['_id'])
            
            unread_count = self.get_unread_count(conv['conversation_id'], user_id)
            
            results.append({
                'conversation': conv,
                'last_message': last_message,
                'unread_count': unread_count
            })
        
        return results
    
    def mark_messages_read(
        self,
        conversation_id: str,
        user_id: int
    ) -> int:
        result = self.messages.update_many(
            {
                'conversation_id': conversation_id,
                'sender_id': {'$ne': user_id},
                'status': {'$ne': MessageStatus.READ}
            },
            {
                '$set': {
                    'status': MessageStatus.READ,
                    'read_at': datetime.utcnow().isoformat()
                }
            }
        )
        
        return result.modified_count
    
    def mark_message_delivered(
        self,
        message_id: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        try:
            msg_object_id = ObjectId(message_id)
        except Exception:
            return None
        
        message = self.messages.find_one({'_id': msg_object_id})
        
        if not message:
            return None
        
        if message.get('sender_id') == user_id:
            return None
        
        if message.get('status') != MessageStatus.SENT:
            return None
        
        result = self.messages.update_one(
            {
                '_id': msg_object_id,
                'status': MessageStatus.SENT
            },
            {
                '$set': {
                    'status': MessageStatus.DELIVERED,
                    'delivered_at': datetime.utcnow().isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            updated = self.messages.find_one({'_id': msg_object_id})
            return {
                '_id': str(updated['_id']),
                'conversation_id': updated.get('conversation_id'),
                'status': updated.get('status'),
                'delivered_at': updated.get('delivered_at')
            }
        
        return None
    
    def get_unread_count(
        self,
        conversation_id: str,
        user_id: int
    ) -> int:
        count = self.messages.count_documents({
            'conversation_id': conversation_id,
            'sender_id': {'$ne': user_id},
            'status': {'$ne': MessageStatus.READ}
        })
        
        return count

    def is_participant(
        self,
        conversation_id: str,
        user_id: int
    ) -> bool:
        """
        Check if user is a participant in the conversation.

        Args:
            conversation_id: Conversation UUID string
            user_id: User ID to check

        Returns:
            bool: True if user is a participant, False otherwise
        """
        conversation = self.conversations.find_one(
            {'conversation_id': conversation_id},
            {'participants': 1}
        )
        if not conversation:
            return False
        return user_id in conversation.get('participants', [])

    def is_message_participant(
        self,
        message_id: str,
        user_id: int
    ) -> bool:
        """
        Check if user is a participant in the conversation of a given message.

        Args:
            message_id: MongoDB ObjectId as string
            user_id: User ID to check

        Returns:
            bool: True if user is a participant, False otherwise
        """
        try:
            msg = self.messages.find_one(
                {'_id': ObjectId(message_id)},
                {'conversation_id': 1}
            )
            if not msg:
                return False
            return self.is_participant(msg['conversation_id'], user_id)
        except Exception:
            return False


_chat_service = None


def get_chat_service() -> ChatService:
    """Get or create ChatService singleton instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service