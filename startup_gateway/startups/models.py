from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class StartupProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="startup_profile"
    )
    company_name = models.CharField(max_length=255)
    short_pitch = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = "startup_profiles"
        indexes = [
            models.Index(fields=["company_name"]),
        ]

    def __str__(self):
        return self.company_name
