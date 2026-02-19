from django.utils import timezone
from rest_framework.exceptions import ValidationError


def publish_startup_profile(profile, actor):
    missing = profile.get_missing_publish_fields()

    if missing:
        raise ValidationError({
            "missing_fields": missing
        })

    profile.is_published = True
    profile.published_at = timezone.now()
    profile.published_by = actor
    profile.save(update_fields=[
        "is_published",
        "published_at",
        "published_by"
    ])

    return profile