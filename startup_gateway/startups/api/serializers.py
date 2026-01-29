from rest_framework import serializers
from projects.models import Project, ProjectStatus

class ProjectSummarySerializer(serializers.ModelSerializer):
    """Serializer for displaying project as a card"""
    
    thumbnail = serializers.SerializerMethodField()
    short_desc = serializers.CharField(source='short_description')
    status = serializers.ChoiceField(choices=ProjectStatus.choices)
    
    class Meta:
        model = Project
        fields = ['id', 'title', 'status', 'thumbnail', 'short_desc']
        read_only_fields = fields
    
    def get_thumbnail(self, obj):
        """Returns thumbnail URL or None"""
        if obj.thumbnail_url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail_url)
            return obj.thumbnail_url
        return None