from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    project_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "project_id",
            "payload",
            "is_read",
            "created_at",
        )
        read_only_fields = fields

    def get_project_id(self, obj):
        return obj.project_id
