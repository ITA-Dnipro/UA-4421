from rest_framework import serializers
from .models import StartupProfile
from projects.models import Tag


class StartupPublicSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()

    class Meta:
        model = StartupProfile
        fields = (
            'id',
            'company_name',
            'slug',
            'hero_image_url',
            'logo_url',
            'short_pitch',
            'about',
            'contact',
            'website',
            'tags',
            'followers_count',
            'projects_count',
            'created_at',
        )

    def get_contact(self, obj):
        return {
            'email': obj.contact_email,
            'phone': obj.contact_phone
        }

    def get_followers_count(self, obj):
        return obj.saved_by_investors.count()

    def get_projects_count(self, obj):
        return obj.projects.count()

    def get_tags(self, obj):
        return (
            Tag.objects
            .filter(projects__startup_profile=obj)
            .values_list('name', flat=True)
            .distinct()
        )
