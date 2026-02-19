import os
from django.utils import timezone
import uuid
from django.db import models


def upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lstrip(".")
    return f"uploads/{timezone.now():%Y/%m}/{uuid.uuid4()}.{ext}"


class Upload(models.Model):
    file = models.FileField(upload_to=upload_to)
    type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)