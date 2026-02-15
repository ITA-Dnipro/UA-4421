from rest_framework import serializers
from django.conf import settings

from .models import StartupProfile
from uploads.models import Upload


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
            'about_html',
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
        tags = set()
        for project in obj.projects.all():
            tags.update(project.tags.values_list('name', flat=True))
        return list(tags)
    

class StartupListSerializer(serializers.ModelSerializer):
    short_description = serializers.CharField(source='short_pitch', read_only=True)
    thumbnail_url = serializers.CharField(source='logo_url', read_only=True)
    regions = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = StartupProfile
        fields = (
            'id',
            'company_name',
            'short_description',
            'thumbnail_url',
            'regions',
            'tags',
        )

    def get_regions(self, obj):
        return list(
            obj.region
            .values_list('name', flat=True)
            .distinct()
        )

    def get_tags(self, obj):
        return list(
            obj.projects
            .values_list('tags__name', flat=True)
            .distinct()
        )

class StartupProfileMeSerializer(serializers.ModelSerializer):
    logo_upload_id = serializers.IntegerField(required=False, write_only=True)
    pitch_deck_upload_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = StartupProfile
        fields = (
            "company_name",
            "slug",
            "short_pitch",
            "about_html",
            "website",
            "contact_email",
            "contact_phone",
            "hero_image_url",
            "logo_url",
            "pitch_deck_url",
            "logo_upload_id",
            "pitch_deck_upload_id",
        )
        read_only_fields = ("company_name", "slug", "logo_url", "pitch_deck_url")

    def _abs_url(self, rel_url: str) -> str:
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(rel_url)
        base = getattr(settings, "APP_BASE_URL", "http://localhost:8000").rstrip("/")
        return f"{base}{rel_url}"

    def update(self, instance, validated_data):
        logo_upload_id = validated_data.pop("logo_upload_id", None)
        pitch_deck_upload_id = validated_data.pop("pitch_deck_upload_id", None)

        for k, v in validated_data.items():
            setattr(instance, k, v)

        if logo_upload_id is not None:
            try:
                upload = Upload.objects.get(id=logo_upload_id)
            except Upload.DoesNotExist:
                raise serializers.ValidationError({"logo_upload_id": "Upload not found."})

            if upload.type != "image":
                raise serializers.ValidationError({"logo_upload_id": "Upload is not an image."})

            instance.logo_url = self._abs_url(upload.file.url)

        if pitch_deck_upload_id is not None:
            try:
                upload = Upload.objects.get(id=pitch_deck_upload_id)
            except Upload.DoesNotExist:
                raise serializers.ValidationError({"pitch_deck_upload_id": "Upload not found."})

            if upload.type != "doc":
                raise serializers.ValidationError({"pitch_deck_upload_id": "Upload is not a document."})

            instance.pitch_deck_url = self._abs_url(upload.file.url)

        instance.save()
        return instance