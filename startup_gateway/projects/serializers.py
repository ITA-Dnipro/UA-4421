from rest_framework import serializers
from projects.models import  ProjectStatus
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "thumbnail_url", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at"]
        read_only_fields = ["id", "created_at", "raised_amount"]
        extra_kwargs = {
            "status": {"required": False},
        }

class ProjectDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "thumbnail_url", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at", "updated_at", "startup_profile_id"]
        read_only_fields = ["id", "created_at", "updated_at", "startup_profile_id", "raised_amount"]
        extra_kwargs = {
            "status": {"required": False},
        }

class ProjectStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProjectStatus.choices)

class ProjectRaisedAmountUpdateSerializer(serializers.Serializer):
    raised_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0
    )