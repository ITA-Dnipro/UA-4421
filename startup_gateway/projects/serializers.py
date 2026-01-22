from rest_framework import serializers

from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "status": {"required": False},
        }

class ProjectDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "slug", "title", "short_description", "description", "status", "raised_amount", "target_amount", "currency", "visibility", "created_at", "updated_at", "startup_profile_id"]
        read_only_fields = ["created_at", "updated_at", "startup_profile_id"]
        extra_kwargs = {
            "status": {"required": False},
        }