from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=50)
    payload = models.JSONField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"{self.type} for {self.user}"
