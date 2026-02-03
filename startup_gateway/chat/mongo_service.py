"""Minimal service layer for MongoDB chat operations.

Only basic operations for task acceptance criteria:
- create_conversation
- send_message
- get_conversation
- get_messages
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
    """Minimal service for managing conversations in MongoDB."""
    
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
        """
        Create a new conversation.
        
        Args:
            participants: List of user IDs
            project_id: Optional project UUID
            startup_id: Optional startup UUID
            meta: Optional metadata
            
        Returns:
            str: Conversation UUID (conversation_id field)
        """
        conversation = Conversation(
            participants=participants,
            project_id=project_id,
            startup_id=startup_id,
            meta=meta or {}
        )
        
        self.conversations.insert_one(conversation.to_dict())
        return conversation.conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by UUID.
        
        Args:
            conversation_id: Conversation UUID string
            
        Returns:
            Dict or None: Conversation document
        """
        try:
            result = self.conversations.find_one({'conversation_id': conversation_id})
            if result:
                result['_id'] = str(result['_id'])
            return result
        except PyMongoError:
            return None
    
    def send_message(
        self,
        conversation_id: str,
        sender_id: int,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send a message in a conversation.
        
        Args:
            conversation_id: Conversation UUID string
            sender_id: User ID of sender
            body: Message text
            attachments: Optional list of attachments [{upload_id, url, type}]
            meta: Optional metadata
            
        Returns:
            str: Message MongoDB _id (ObjectId as string)
        """
        
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
        message_id = str(result.inserted_id)
        
        
        self.conversations.update_one(
            {'conversation_id': conversation_id},
            {
                '$set': {
                    'last_message_at': datetime.utcnow().isoformat()
                }
            }
        )
        
        return message_id
    
    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation UUID string
            limit: Maximum number of messages
            skip: Number of messages to skip
            
        Returns:
            List[Dict]: List of message documents
        """
        query = {'conversation_id': conversation_id}
        
        cursor = self.messages.find(query)\
            .sort('created_at', -1)\
            .limit(limit)\
            .skip(skip)
        
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            results.append(doc)
        
        
        return list(reversed(results))



_chat_service = None


def get_chat_service() -> ChatService:
    """Get or create ChatService instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
