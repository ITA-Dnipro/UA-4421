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