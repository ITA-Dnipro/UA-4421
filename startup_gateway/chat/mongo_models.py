"""
MongoDB schemas for chat collections 

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
    upload_id: str  
    url: str
    type: str  
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
    participants: List[int]  
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))  
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    project_id: Optional[str] = None  
    startup_id: Optional[str] = None  
    meta: Dict[str, Any] = field(default_factory=dict)  
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion."""
        data = {
            'conversation_id': self.conversation_id,
            'participants': self.participants,  
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'meta': self.meta,
        }
        
        
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
    conversation_id: str  
    sender_id: int  
    body: str  
    attachments: List[Attachment] = field(default_factory=list)
    status: str = MessageStatus.SENT  
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    meta: Dict[str, Any] = field(default_factory=dict)  
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion."""
        data = {
            'conversation_id': self.conversation_id,  
            'sender_id': self.sender_id,
            'body': self.body,  
            'attachments': [a.to_dict() if isinstance(a, Attachment) else a for a in self.attachments],
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'meta': self.meta,
        }
        
        if self.delivered_at:
            data['delivered_at'] = self.delivered_at.isoformat() if isinstance(self.delivered_at, datetime) else self.delivered_at
        if self.read_at:
            data['read_at'] = self.read_at.isoformat() if isinstance(self.read_at, datetime) else self.read_at
            
        return data



CONVERSATIONS_COLLECTION = 'conversations'
MESSAGES_COLLECTION = 'messages'