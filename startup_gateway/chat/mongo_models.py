"""
MongoDB schemas for chat collections - TASK SPECIFICATION COMPLIANT.

Matches exact schema from task requirements.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


class MessageStatus(str):
    """Message delivery status constants."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


class AttachmentType(str):
    """Type of message attachment constants."""
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class Attachment:
    """
    Message attachment schema - MATCHES TASK SPEC.
    
    Task spec: {"upload_id": "...", "url":"...", "type":"image"}
    """
    upload_id: str  # ← REQUIRED by task
    url: str
    type: str  # image, document, video, audio
    filename: Optional[str] = None
    size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Conversation:
    """
    Conversation document schema - MATCHES TASK SPEC.
    
    Task spec:
    {
      "_id": ObjectId,
      "conversation_id": "uuid",
      "participants": [user_id,...],
      "project_id": uuid|null,
      "startup_id": uuid|null,
      "created_at": ISODate,
      "last_message_at": ISODate,
      "meta": {...}
    }
    """
    participants: List[int]  # Simple array of user_ids (NOT objects!)
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Auto-generate UUID
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    project_id: Optional[str] = None  # UUID string or null
    startup_id: Optional[str] = None  # UUID string or null
    meta: Dict[str, Any] = field(default_factory=dict)  # meta, NOT metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion."""
        data = {
            'conversation_id': self.conversation_id,
            'participants': self.participants,  # Simple array
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'meta': self.meta,
        }
        
        # Add optional fields
        if self.last_message_at:
            data['last_message_at'] = self.last_message_at.isoformat() if isinstance(self.last_message_at, datetime) else self.last_message_at
        if self.project_id:
            data['project_id'] = self.project_id
        if self.startup_id:
            data['startup_id'] = self.startup_id
            
        return data


@dataclass
class Message:
    """
    Message document schema - MATCHES TASK SPEC.
    
    Task spec:
    {
      "_id": ObjectId,
      "conversation_id": "uuid",
      "sender_id": user_id,
      "body": "string",
      "attachments": [{"upload_id": "...", "url":"...", "type":"image"}],
      "status": "sent|delivered|read",
      "created_at": ISODate,
      "meta": {...}
    }
    """
    conversation_id: str  # UUID string (matches conversation.conversation_id)
    sender_id: int  # User ID
    body: str  # Message text (NOT "content"!)
    attachments: List[Attachment] = field(default_factory=list)
    status: str = MessageStatus.SENT  # "sent" | "delivered" | "read"
    created_at: datetime = field(default_factory=datetime.utcnow)
    meta: Dict[str, Any] = field(default_factory=dict)  # meta, NOT metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion."""
        return {
            'conversation_id': self.conversation_id,  # UUID string
            'sender_id': self.sender_id,
            'body': self.body,  # NOT "content"
            'attachments': [a.to_dict() if isinstance(a, Attachment) else a for a in self.attachments],
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'meta': self.meta,
        }


# Collection names
CONVERSATIONS_COLLECTION = 'conversations'
MESSAGES_COLLECTION = 'messages'
