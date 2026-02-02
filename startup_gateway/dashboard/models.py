from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class SavedItem(models.Model):
    investor_profile = models.ForeignKey(
        'investors.InvestorProfile',
        on_delete=models.CASCADE,
        related_name='saved_items'
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    target = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_items'
        unique_together = ('investor_profile', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.investor_profile} saved {self.content_type.app_label}.{self.content_type.model}#{self.object_id}"
