from datetime import timezone
import uuid
from django.db import models


def upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1]
    return f"uploads/{timezone.now():%Y/%m}/{uuid.uuid4()}.{ext}"


class Upload(models.Model):
    file = models.FileField(upload_to=upload_to)
    mime_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)