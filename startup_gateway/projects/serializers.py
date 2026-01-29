from rest_framework import serializers
from projects.models import  ProjectStatus

class ProjectStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProjectStatus.choices)