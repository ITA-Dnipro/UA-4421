from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
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
    target_id = serializers.CharField()

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

        try:
            target_obj = model.objects.get(pk=target_id)
        except Exception:
            raise serializers.ValidationError({"target_id": "Target does not exist."})

        if target_type == "company":
            is_startup_user = (
                hasattr(target_obj, "startup_profile") or
                target_obj.roles.filter(name__iexact="startup").exists()
            )
            if not is_startup_user:
                raise serializers.ValidationError({"target_type": "Target user is not a startup/company."})

            if target_obj.pk == request.user.pk:
                raise serializers.ValidationError("You cannot save your own company.")

        if target_type == "startup":
            if hasattr(request.user, "startup_profile") and request.user.startup_profile.pk == target_obj.pk:
                raise serializers.ValidationError("You cannot save your own startup.")

        if target_type == "project":
            proj = target_obj
            owner_user = getattr(proj.startup_profile, "user", None)
            if owner_user and owner_user.pk == request.user.pk:
                raise serializers.ValidationError("You cannot save your own project.")

        attrs["investor"] = investor
        attrs["content_type"] = ContentType.objects.get_for_model(model)
        attrs["target_id_str"] = str(target_obj.pk)
        attrs["target_obj"] = target_obj
        return attrs