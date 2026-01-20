import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class ProjectStatus(models.TextChoices):
    IDEA = "idea", "Idea"
    PROTOTYPE = "prototype", "Prototype"
    ACTIVE = "active", "Active"
    FUNDED = "funded", "Funded"
    CLOSED = "closed", "Closed"

class ProjectVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted"

class AttachmentType(models.TextChoices):
    THUMBNAIL = "thumbnail", "Thumbnail image"
    DECK = "deck", "Pitch deck"
    
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'tags'

    def __str__(self):
        return self.name

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    startup_profile = models.ForeignKey(
        'startups.StartupProfile',
        on_delete=models.CASCADE,
        related_name="projects"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    short_description = models.TextField(max_length=500)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.IDEA
    )

    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    raised_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    currency = models.CharField(max_length=3, default="UAH")

    visibility = models.CharField(
        max_length=10,
        choices=ProjectVisibility.choices,
        default=ProjectVisibility.PUBLIC
    )

    tags = models.ManyToManyField(
        Tag,
        related_name="projects",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        constraints = [
        models.UniqueConstraint(
            fields=["startup_profile", "slug"],
            name="unique_project_slug_per_startup"
        )
    ]
    indexes = [
        models.Index(fields=["startup_profile"]),
        models.Index(fields=["status"]),
    ]
    def __str__(self):
        return self.title

class ProjectAttachment(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    # upload = models.ForeignKey("uploads.Upload", on_delete=models.CASCADE)   
    type = models.CharField(max_length=10, choices=AttachmentType.choices)
    order = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'project_attachments'
        ordering = ["order"]

class ProjectAudit(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="audit"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()

    class Meta:
        db_table = 'project_audit'