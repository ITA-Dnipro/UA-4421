"""
Django REST Framework serializers - TASK SPECIFICATION COMPLIANT.

Matches exact field names from task: body (not content), meta (not metadata)
"""
from rest_framework import serializers


class AttachmentSerializer(serializers.Serializer):
    """
    Serializer for message attachments - TASK FORMAT.
    
    Task spec: {"upload_id": "...", "url":"...", "type":"image"}
    """
    upload_id = serializers.CharField(max_length=255)  # REQUIRED by task
    url = serializers.URLField()
    type = serializers.ChoiceField(choices=['image', 'document', 'video', 'audio'])
    filename = serializers.CharField(max_length=255, required=False, allow_null=True)
    size = serializers.IntegerField(required=False, allow_null=True)


class ConversationSerializer(serializers.Serializer):
    """
    Serializer for conversation documents - TASK FORMAT.
    
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
    id = serializers.CharField(source='_id', read_only=True)  # MongoDB ObjectId
    conversation_id = serializers.UUIDField(read_only=True)  # UUID for app
    participants = serializers.ListField(
        child=serializers.IntegerField(),
        read_only=True
    )  # Simple array [user_id, ...]
    project_id = serializers.UUIDField(required=False, allow_null=True)
    startup_id = serializers.UUIDField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    last_message_at = serializers.DateTimeField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, default=dict)  # "meta" NOT "metadata"


class CreateConversationSerializer(serializers.Serializer):
    """
    Serializer for creating a new conversation.
    Only investors can create conversations.
    """
    recipient_id = serializers.IntegerField(
        help_text="User ID to start conversation with (should be startup)"
    )
    
    def validate_recipient_id(self, value):
        """Validate recipient exists and is a startup."""
        from users.models import User
        
        try:
            recipient = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient user does not exist")
        
        # Verify recipient has 'startup' role
        if not recipient.roles.filter(name='startup').exists():
            raise serializers.ValidationError("Can only start conversations with startups")
        
        return value


class MessageSerializer(serializers.Serializer):
    """
    Serializer for message documents - TASK FORMAT.
    
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
    id = serializers.CharField(source='_id', read_only=True)  # MongoDB ObjectId
    conversation_id = serializers.UUIDField()  # UUID string (NOT ObjectId!)
    sender_id = serializers.IntegerField()
    body = serializers.CharField()  # "body" NOT "content"
    attachments = AttachmentSerializer(many=True, required=False, default=list)
    status = serializers.ChoiceField(
        choices=['sent', 'delivered', 'read'],
        default='sent'
    )
    created_at = serializers.DateTimeField(read_only=True)
    meta = serializers.DictField(required=False, default=dict)  # "meta" NOT "metadata"


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a new message - TASK FORMAT."""
    conversation_id = serializers.UUIDField()  # UUID string
    body = serializers.CharField(min_length=1, max_length=5000)  # "body" NOT "content"
    attachments = AttachmentSerializer(many=True, required=False, default=list)
    meta = serializers.DictField(required=False, default=dict)


class UpdateMessageStatusSerializer(serializers.Serializer):
    """Serializer for updating message status."""
    status = serializers.ChoiceField(choices=['sent', 'delivered', 'read'])


class MessageListSerializer(serializers.Serializer):
    """Serializer for message list query parameters."""
    limit = serializers.IntegerField(default=50, min_value=1, max_value=100)
    skip = serializers.IntegerField(default=0, min_value=0)
    before_id = serializers.CharField(
        required=False,
        help_text="Message ObjectId to get messages before"
    )


class ConversationListSerializer(serializers.Serializer):
    """Serializer for conversation list query parameters."""
    limit = serializers.IntegerField(default=50, min_value=1, max_value=100)
    skip = serializers.IntegerField(default=0, min_value=0)
