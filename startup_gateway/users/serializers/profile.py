import re
from urllib.parse import urlparse

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction

from projects.models import Tag

User = get_user_model()


class UserStatsMixin(serializers.Serializer):
    stats = serializers.SerializerMethodField()

    def get_stats(self, obj):
        return {
            "projects_count": getattr(obj, "projects_count", 0),
            "followers": getattr(obj, "followers_count", 0),
            "views": getattr(obj, "views_count", 0),
        }


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")


class PublicProfileSerializer(UserStatsMixin, serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "slug",
            "about_html",
            "short_description",
            "contact",
            "website",
            "tags",
            "stats",
            "media_urls",
            "visibility",
        )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = User
        fields = (
            "slug",
            "about_html",
            "short_description",
            "contact",
            "website",
            "tags",
            "media_urls",
            "visibility",
        )

    # ---------- FIELD VALIDATION ----------

    def validate_slug(self, value: str):
        value = value.strip().lower()

        if not re.match(r"^[a-z0-9-]+$", value):
            raise serializers.ValidationError(
                "Slug may contain only lowercase letters, numbers and hyphens."
            )

        return value

    def validate_media_urls(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("media_urls must be a list.")

        for url in value:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise serializers.ValidationError(
                    f"Invalid URL in media_urls: {url}"
                )

        return value

    def validate_contact(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("contact must be an object.")

        allowed_keys = {"email", "phone", "telegram", "linkedin"}
        unknown_keys = set(value.keys()) - allowed_keys

        if unknown_keys:
            raise serializers.ValidationError(
                f"Unsupported contact fields: {', '.join(unknown_keys)}"
            )

        return value

    # ---------- OBJECT-LEVEL VALIDATION ----------

    def validate(self, attrs):
        """
        Enforce PUT semantics:
        PUT (partial=False) must include required fields.
        PATCH (partial=True) may update partially.
        """
        if not self.partial:
            required_fields = {
                "slug",
                "short_description",
                "visibility",
            }

            missing = required_fields - set(attrs.keys())
            if missing:
                raise serializers.ValidationError(
                    {field: "This field is required." for field in missing}
                )

        return attrs

    # ---------- UPDATE ----------

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            if tags is not None:
                instance.tags.set(tags)

        return instance
