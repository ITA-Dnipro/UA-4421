from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from startups.models import StartupProfile
from projects.models import Project

User = get_user_model()

TARGET_MAP = {
    "startup": StartupProfile,
    "project": Project,
    "company": User,
}


class SavedItemCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=list(TARGET_MAP.keys()))
    target_id = serializers.UUIDField()

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None:
            raise serializers.ValidationError("Request is required in context.")

        investor = getattr(request.user, "investor_profile", None)
        if investor is None:
            raise serializers.ValidationError("Investor profile does not exist for this user.")

        target_type = attrs["target_type"]
        target_id = attrs["target_id"]
        model = TARGET_MAP[target_type]

        lookup_field = "id" if target_type == "project" else "uuid"

        try:
            target_obj = model.objects.get(**{lookup_field: target_id})
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"target_id": "Target does not exist."})

        if attrs["target_type"] == "company":
            if not target_obj.is_startup():
                raise serializers.ValidationError("Target user is not a startup/company.")

            if target_obj.id == request.user.id:
                raise serializers.ValidationError("You cannot save your own company.")
        
        if attrs["target_type"] == "startup":
            if hasattr(request.user, "startup_profile") and \
               request.user.startup_profile.uuid == target_obj.uuid:
                raise serializers.ValidationError("You cannot save your own startup.")

        if attrs["target_type"] == "project":
            owner = target_obj.startup_profile.user
            if owner.id == request.user.id:
                raise serializers.ValidationError("You cannot save your own project.")

        attrs["investor"] = investor
        attrs["content_type"] = ContentType.objects.get_for_model(model)
        attrs["object_id"] = getattr(target_obj, lookup_field)
        return attrs
    

class SavedItemListSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="object_id", read_only=True)
    saved_id = serializers.IntegerField(source="id")
    type = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    saved_at = serializers.DateTimeField(source="created_at")


    def get_type(self, obj):
        model = obj.content_type.model
        if model == "startupprofile":
            return "startup"
        if model == "project":
            return "project"
        if model == "user":
            return "company"
        return model

    def _target(self, obj):
        return obj.target

    def get_title(self, obj):
        t = self._target(obj)
        if hasattr(t, "title"):
            return t.title
        if hasattr(t, "company_name"):
            return t.company_name
        if hasattr(t, "username"):
            return t.username
        return ""

    def get_slug(self, obj):
        t = self._target(obj)
        return getattr(t, "slug", "")

    def get_thumbnail_url(self, obj):
        t = self._target(obj)
        return getattr(t, "thumbnail_url", "") or getattr(t, "logo_url", "")

    def get_short_description(self, obj):
        t = self._target(obj)
        return getattr(t, "short_description", "") or getattr(t, "short_pitch", "")

    def get_location(self, obj):
        t = self._target(obj)
        if hasattr(t, "region"):
            regions = t.region.values_list("name", flat=True)
            return ", ".join(regions)
        return ""

    def get_tags(self, obj):
        content_type = obj.content_type.model
        object_id = obj.object_id

        if content_type == "project":
            project = Project.objects.filter(id=object_id).first()
            return list(
                project.tags
                .values_list("name", flat=True)
                .distinct()
            )

        if content_type == "startupprofile":
            startup = StartupProfile.objects.filter(uuid=object_id).first()
            return list(
                startup.projects
                .values_list("tags__name", flat=True)
                .distinct()
            )

        if content_type == "user":
            user = User.objects.filter(uuid=object_id).first()
            return list(
                user.startup_profile.projects
                .values_list("tags__name", flat=True)
                .distinct()
            )

        return []