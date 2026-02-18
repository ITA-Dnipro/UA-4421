from rest_framework import serializers


class PaginationQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class ConversationCreateSerializer(serializers.Serializer):
    participants = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=2,
    )
    project_id = serializers.UUIDField(required=False, allow_null=True)
    startup_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_participants(self, participants):
        request = self.context.get("request")
        if request and request.user.id not in participants:
            raise serializers.ValidationError("You must be a participant of the conversation.")
        return list(set(participants))

    def validate(self, attrs):

        request = self.context.get("request")
        participants = set(attrs["participants"])

        if request and request.user.id not in participants:
            raise serializers.ValidationError(
                "You must be a participant of the conversation."
            )

        return attrs


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000, trim_whitespace=True)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message body cannot be empty.")
        return value.strip()
    
    def validate_attachments(self, value):
        for attachment in value:
            for field in ['upload_id', 'url', 'type']:
                if field not in attachment:
                    raise serializers.ValidationError(
                        f"Attachment must contain '{field}'."
                    )
        return value
    

class AttachmentSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    url = serializers.URLField()
    type = serializers.ChoiceField(choices=['image', 'document', 'video', 'audio'])
    filename = serializers.CharField(required=False)
    size = serializers.IntegerField(required=False)


class MessageResponseSerializer(serializers.Serializer):
    _id = serializers.CharField()
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
