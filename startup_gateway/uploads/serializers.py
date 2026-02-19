from rest_framework import serializers
from .models import Upload

class UploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Upload
        fields = [
            "id",
            "file",
            "file_url",
            "type",
            "size",
            "content_type",
            "created_at",
        ]

    def get_file_url(self, obj):
        try:
            url = obj.file.url
        except Exception:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url