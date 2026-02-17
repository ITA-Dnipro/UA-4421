from rest_framework import serializers
from projects.models import ModerationAction, Project, ProjectStatus, ProjectVisibility, ProjectAttachment, ProjectAudit
from uploads.models import Upload

class ProjectAttachmentSerializer(serializers.ModelSerializer):
    upload = serializers.PrimaryKeyRelatedField(
    queryset=Upload.objects.all()
    )
    
    class Meta:
        model = ProjectAttachment
        fields = '__all__'

class ProjectAttachmentURLSerializer(serializers.ModelSerializer):
    upload_url = serializers.CharField(
        source="upload.file.url",
        read_only=True
    )
    
    class Meta:
        model = ProjectAttachment
        fields = ["upload_url"]

class ProjectSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "thumbnail_url", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at", "tags"]
        read_only_fields = ["id", "created_at", "raised_amount"]
        extra_kwargs = {
            "status": {"required": False},
        }

class ProjectDetailsSerializer(serializers.ModelSerializer):
    attachments = ProjectAttachmentURLSerializer(many=True, read_only=True)

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "thumbnail_url", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at", "updated_at", "startup_profile_id", "tags", "attachments"]
        read_only_fields = ["id", "created_at", "updated_at", "startup_profile_id", "raised_amount"]
        extra_kwargs = {
            "status": {"required": False},
        }

class ProjectStateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ProjectStatus.choices,
        required=False
    )
    raised_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False
    )
    visibility = serializers.ChoiceField(
        choices=ProjectVisibility.choices,
        required=False
    )

    def validate(self, attrs):
        if not any(field in attrs for field in ("status", "raised_amount", "visibility")):
            raise serializers.ValidationError(
                "At least one field (status or raised_amount) must be provided."
            )
        return attrs


class AdminProjectListSerializer(serializers.ModelSerializer):
    startup = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'slug', 'startup', 'owner_email',
            'moderation_status', 'is_deleted', 'created_at',
            'moderated_at', 'tags', 'target_amount', 'raised_amount'
        ]

    def get_startup(self, obj):
        return {
            'id': obj.startup_profile.id,
            'company_name': obj.startup_profile.company_name
        }

    def get_owner_email(self, obj):
        return obj.startup_profile.user.email

    def get_tags(self, obj):
        return list(obj.tags.values_list('name', flat=True))

class ModerationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[ModerationAction.APPROVE, ModerationAction.REJECT, ModerationAction.FLAG],
        required=True
    )
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, data):
        action = data.get('action')
        reason = data.get('reason', '').strip()

        if action == ModerationAction.REJECT and not reason:
            raise serializers.ValidationError({
                'reason': 'Reason is required when rejecting a project'
            })
        return data


class ProjectAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAudit
        fields = ["id", "user", "action", "changes", "created_at"]
        read_only_fields = fields