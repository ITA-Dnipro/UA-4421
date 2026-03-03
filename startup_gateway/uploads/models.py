import os
from django.utils import timezone
import uuid
from django.db import models
from django.conf import settings 


def upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lstrip(".")
    return f"uploads/{timezone.now():%Y/%m}/{uuid.uuid4()}.{ext}"


class Upload(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploads"
    )
    file = models.FileField(upload_to=upload_to)
    type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)