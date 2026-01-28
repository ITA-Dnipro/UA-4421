from rest_framework import serializers
from django.contrib.auth import get_user_model
from projects.models import Tag

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")


class PublicProfileSerializer(serializers.ModelSerializer):
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

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        return instance