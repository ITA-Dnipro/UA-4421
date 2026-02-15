from rest_framework import serializers


class PaginationQuerySerializer(serializers.Serializer):    
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="Page number (1-indexed)"
    )
    page_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Number of items per page (max: 100)"
    )


class ConversationCreateSerializer(serializers.Serializer):
    participants = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=2,  
        help_text="List of user IDs (at least 2 participants required)"
    )
    project_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional UUID of related project"
    )
    startup_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional UUID of related startup"
    )

    def validate_participants(self, value):
        unique_participants = list(set(value))
        
        if len(unique_participants) < 2:
            raise serializers.ValidationError(
                "A conversation must have at least 2 unique participants."
            )
        
        return unique_participants


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(
        max_length=5000,
        trim_whitespace=True,
        help_text="Message text (max 5000 characters)"
    )
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Optional list of attachments"
    )

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Message body cannot be empty or whitespace only."
            )
        return value.strip()

    def validate_attachments(self, value):
        for attachment in value:
            required_fields = ['upload_id', 'url', 'type']
            for field in required_fields:
                if field not in attachment:
                    raise serializers.ValidationError(
                        f"Attachment must contain '{field}' field."
                    )
            
            valid_types = ['image', 'document', 'video', 'audio']
            if attachment['type'] not in valid_types:
                raise serializers.ValidationError(
                    f"Attachment type must be one of: {', '.join(valid_types)}"
                )
        
        return value


class AttachmentSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    url = serializers.URLField()
    type = serializers.ChoiceField(choices=['image', 'document', 'video', 'audio'])
    filename = serializers.CharField(required=False)
    size = serializers.IntegerField(required=False)


class MessageResponseSerializer(serializers.Serializer):
    _id = serializers.CharField(help_text="MongoDB ObjectId")
    conversation_id = serializers.UUIDField()
    sender_id = serializers.IntegerField()
    body = serializers.CharField()
    status = serializers.ChoiceField(choices=['sent', 'delivered', 'read'])
    created_at = serializers.DateTimeField()
    attachments = AttachmentSerializer(many=True)
    meta = serializers.DictField()


class ConversationResponseSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    participants = serializers.ListField(child=serializers.IntegerField())
    created_at = serializers.DateTimeField()
    last_message_at = serializers.DateTimeField(allow_null=True)
    project_id = serializers.UUIDField(allow_null=True)
    startup_id = serializers.UUIDField(allow_null=True)
    meta = serializers.DictField()


class ConversationListItemSerializer(serializers.Serializer):
    conversation = ConversationResponseSerializer()
    last_message = MessageResponseSerializer(allow_null=True)
    unread_count = serializers.IntegerField(min_value=0)