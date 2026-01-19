import uuid
from django.db import models

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'tags'

    def __str__(self):
        return self.name

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    startup_profile = models.ForeignKey( 'startups.StartupProfile', on_delete=models.CASCADE,
        related_name='projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, default='idea')
    thumbnail_url = models.URLField(blank=True)
    tags = models.ManyToManyField(Tag, related_name='projects', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        indexes = [
            models.Index(fields=['title']),
        ]

    def __str__(self):
        return self.title
