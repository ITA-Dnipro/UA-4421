from projects.models import Project, ProjectStatus, ProjectVisibility
from rest_framework import serializers


class ProjectSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Project
        fields = [
            "id",
            "slug",
            "title",
            "short_description",
            "description",
            "thumbnail_url",
            "status",
            "raised_amount",
            "target_amount",
            "currency",
            "visibility",
            "created_at",
            "tags",
        ]
        read_only_fields = ["id", "created_at", "raised_amount"]
        extra_kwargs = {
            "status": {"required": False},
        }


class ProjectDetailsSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Project
        fields = [
            "id",
            "slug",
            "title",
            "short_description",
            "description",
            "thumbnail_url",
            "status",
            "raised_amount",
            "target_amount",
            "currency",
            "visibility",
            "created_at",
            "updated_at",
            "startup_profile_id",
            "tags",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "startup_profile_id",
            "raised_amount",
        ]
        extra_kwargs = {
            "status": {"required": False},
        }


class ProjectStateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=False)
    raised_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    visibility = serializers.ChoiceField(
        choices=ProjectVisibility.choices, required=False
    )

    def validate(self, attrs):
        if not any(
            field in attrs for field in ("status", "raised_amount", "visibility")
        ):
            raise serializers.ValidationError(
                "At least one field (status or raised_amount) must be provided."
            )
        return attrs
