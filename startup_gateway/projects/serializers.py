from rest_framework import serializers
from projects.models import  ProjectStatus, Project, ProjectModerationLog, ModerationStatus, ModerationAction
from .models import Project
from startups.models import StartupProfile

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
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "thumbnail_url", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at", "updated_at", "startup_profile_id", "tags"]
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

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one field (status or raised_amount) must be provided."
            )
        return attrs


class AdminProjectListSerializer(serializers.ModelSerializer):
    startup = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    moderated_by_username = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'startup',
            'owner_email',
            'status',
            'moderation_status',
            'visibility',
            'is_deleted',
            'created_at',
            'moderated_at',
            'moderated_by_username',
            'tags',
            'target_amount',
            'raised_amount',
        ]

    def get_startup(self, obj):
        return {
            'id': obj.startup_profile.id,
            'company_name': obj.startup_profile.company_name,
            'slug': obj.startup_profile.slug
        }

    def get_owner_email(self, obj):
        return obj.startup_profile.user.email

    def get_moderated_by_username(self, obj):
        if obj.moderated_by:
            return obj.moderated_by.username
        return None

    def get_tags(self, obj):
        return list(obj.tags.values_list('name', flat=True))


class AdminProjectDetailSerializer(serializers.ModelSerializer):
    startup = serializers.SerializerMethodField()
    moderated_by = serializers.SerializerMethodField()
    deleted_by = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    moderation_history = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'

    def get_startup(self, obj):
        startup = obj.startup_profile
        return {
            'id': startup.id,
            'company_name': startup.company_name,
            'slug': startup.slug,
            'user_id': startup.user.id,
            'user_email': startup.user.email,
            'user_verified': startup.user.verified,
        }

    def get_moderated_by(self, obj):
        if obj.moderated_by:
            return {
                'id': obj.moderated_by.id,
                'username': obj.moderated_by.username,
                'email': obj.moderated_by.email,
            }
        return None

    def get_deleted_by(self, obj):
        if obj.deleted_by:
            return {
                'id': obj.deleted_by.id,
                'username': obj.deleted_by.username,
            }
        return None

    def get_tags(self, obj):
        return list(obj.tags.values_list('name', flat=True))

    def get_moderation_history(self, obj):
        logs = obj.moderation_logs.select_related('moderator').order_by('-created_at')[:10]
        return ModerationLogSerializer(logs, many=True).data


class ModerationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            ModerationAction.APPROVE,
            ModerationAction.REJECT,
            ModerationAction.FLAG,
            ModerationAction.RESTORE,
            ModerationAction.DELETE,
        ],
        required=True,
        help_text="Action to perform: approve, reject, flag, restore, or delete"
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Reason for the action (required for reject)"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text="Internal notes (optional)"
    )

    def validate(self, data):
        action = data.get('action')
        reason = data.get('reason', '').strip()

        # Reject requires reason
        if action == ModerationAction.REJECT and not reason:
            raise serializers.ValidationError({
                'reason': 'Reason is required when rejecting a project'
            })

        return data


class ModerationLogSerializer(serializers.ModelSerializer):
    moderator_username = serializers.CharField(
        source='moderator.username',
        read_only=True
    )
    project_title = serializers.CharField(
        source='project.title',
        read_only=True
    )

    class Meta:
        model = ProjectModerationLog
        fields = [
            'id',
            'project',
            'project_title',
            'action',
            'moderator',
            'moderator_username',
            'reason',
            'notes',
            'old_status',
            'new_status',
            'created_at',
        ]


class BulkModerationSerializer(serializers.Serializer):
    project_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100,
        help_text="List of project IDs to moderate"
    )
    action = serializers.ChoiceField(
        choices=[
            ModerationAction.APPROVE,
            ModerationAction.REJECT,
            ModerationAction.FLAG,
            ModerationAction.DELETE,
        ],
        required=True
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
