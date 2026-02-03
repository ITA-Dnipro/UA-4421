"""
Service layer for chat operations - TASK SPECIFICATION COMPLIANT.

- Uses exact schema from task (UUID conversation_id, simple participants array, meta)
- Simplified: only 1-on-1 conversations
- Only investors can initiate conversations
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
    """Service for managing 1-on-1 conversations in MongoDB."""
    
    def __init__(self):
        """Initialize with MongoDB database connection."""
        self.db = get_mongo_db()
        self.conversations = self.db[CONVERSATIONS_COLLECTION]
        self.messages = self.db[MESSAGES_COLLECTION]
    
    # ==================== CONVERSATION METHODS ====================
    
    def create_conversation(
        self,
        initiator_id: int,
        recipient_id: int,
    ) -> str:
        """
        Create a new 1-on-1 conversation.
        Only investors can initiate conversations.
        
        Args:
            initiator_id: User ID who starts the conversation (must be investor)
            recipient_id: User ID to chat with (should be startup)
            
        Returns:
            str: Conversation UUID (conversation_id field)
            
        Raises:
            PermissionError: If initiator is not an investor
            ValueError: If trying to chat with yourself
        """
        from users.models import User
        
        # Validation: can't chat with yourself
        if initiator_id == recipient_id:
            raise ValueError("Cannot create conversation with yourself")
        
        # Check if initiator is an investor
        try:
            initiator = User.objects.get(id=initiator_id)
            if not initiator.roles.filter(name='investor').exists():
                raise PermissionError("Only investors can start conversations")
        except User.DoesNotExist:
            raise ValueError(f"User {initiator_id} does not exist")
        
        # Check if conversation already exists between these users
        existing = self.conversations.find_one({
            'participants': {'$all': [initiator_id, recipient_id]}
        })
        
        if existing:
            return existing['conversation_id']  # Return existing UUID
        
        # Create new conversation with UUID
        conversation = Conversation(
            conversation_id=str(uuid.uuid4()),  # Generate UUID
            participants=[initiator_id, recipient_id],  # Simple array
            project_id=None,  # Can be set later if needed
            startup_id=None,  # Can be set later if needed
            meta={
                'initiator_id': initiator_id,
                'created_by_investor': True
            }
        )
        
        self.conversations.insert_one(conversation.to_dict())
        return conversation.conversation_id  # Return UUID
    
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
    
    def get_conversation_between_users(
        self,
        user1_id: int,
        user2_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find conversation between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            Dict or None: Conversation document
        """
        result = self.conversations.find_one({
            'participants': {'$all': [user1_id, user2_id]}
        })
        
        if result:
            result['_id'] = str(result['_id'])
        
        return result
    
    def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            List[Dict]: List of conversation documents
        """
        cursor = self.conversations.find({'participants': user_id})\
            .sort('last_message_at', -1)\
            .limit(limit)\
            .skip(skip)
        
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            results.append(doc)
        
        return results
    
    # ==================== MESSAGE METHODS ====================
    
    def send_message(
        self,
        conversation_id: str,  # UUID string
        sender_id: int,
        body: str,  # Task spec uses "body" not "content"
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
            meta: Optional additional data
            
        Returns:
            str: Message MongoDB _id (ObjectId as string)
        """
        # Verify conversation exists
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        # Verify sender is in conversation
        if sender_id not in conversation['participants']:
            raise PermissionError("User is not a participant in this conversation")
        
        # Create attachments
        attachment_objects = []
        if attachments:
            for att in attachments:
                attachment_objects.append(Attachment(**att))
        
        # Create message
        message = Message(
            conversation_id=conversation_id,  # UUID string
            sender_id=sender_id,
            body=body,  # NOT "content"
            attachments=attachment_objects,
            meta=meta or {}  # NOT "metadata"
        )
        
        # Insert message
        result = self.messages.insert_one(message.to_dict())
        message_id = str(result.inserted_id)
        
        # Update conversation's last_message_at
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
        conversation_id: str,  # UUID string
        limit: int = 50,
        skip: int = 0,
        before_id: Optional[str] = None  # Message ObjectId
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation UUID string
            limit: Maximum number of messages
            skip: Number of messages to skip
            before_id: Optional message _id to get messages before
            
        Returns:
            List[Dict]: List of message documents
        """
        query = {'conversation_id': conversation_id}  # UUID string
        
        # Add "before" filter if provided
        if before_id:
            query['_id'] = {'$lt': ObjectId(before_id)}
        
        cursor = self.messages.find(query)\
            .sort('created_at', -1)\
            .limit(limit)\
            .skip(skip)
        
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            results.append(doc)
        
        # Return in chronological order
        return list(reversed(results))
    
    def update_message_status(
        self,
        message_id: str,  # Message ObjectId
        status: str  # "sent" | "delivered" | "read"
    ) -> bool:
        """
        Update message status.
        
        Args:
            message_id: Message ObjectId as string
            status: New status (sent, delivered, read)
            
        Returns:
            bool: Success status
        """
        if status not in [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]:
            raise ValueError(f"Invalid status: {status}")
        
        result = self.messages.update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'status': status}}
        )
        
        return result.modified_count > 0
    
    def get_unread_count(self, conversation_id: str, user_id: int) -> int:
        """
        Get count of unread messages for a user in a conversation.
        
        Args:
            conversation_id: Conversation UUID string
            user_id: User ID
            
        Returns:
            int: Count of unread messages
        """
        # Count messages where:
        # - In this conversation
        # - Not sent by this user
        # - Status is not 'read'
        query = {
            'conversation_id': conversation_id,
            'sender_id': {'$ne': user_id},
            'status': {'$ne': MessageStatus.READ}
        }
        
        return self.messages.count_documents(query)
    
    def mark_all_as_read(
        self,
        conversation_id: str,
        user_id: int
    ) -> int:
        """
        Mark all messages in conversation as read for user.
        
        Args:
            conversation_id: Conversation UUID string
            user_id: User ID
            
        Returns:
            int: Number of messages updated
        """
        # Update all messages in conversation not sent by user
        result = self.messages.update_many(
            {
                'conversation_id': conversation_id,
                'sender_id': {'$ne': user_id},
                'status': {'$ne': MessageStatus.READ}
            },
            {
                '$set': {'status': MessageStatus.READ}
            }
        )
        
        return result.modified_count


# Singleton instance
_chat_service = None


def get_chat_service() -> ChatService:
    """Get or create ChatService instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
