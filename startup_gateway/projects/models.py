import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

User = settings.AUTH_USER_MODEL

class ProjectStatus(models.TextChoices):
    IDEA = "idea", "Idea"
    MVP = "mvp", "MVP"
    FUNDRAISING = "fundraising", "Fundraising"
    FUNDED = "funded", "Funded"
    CLOSED = "closed", "Closed"

class ProjectVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted"

class ModerationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    FLAGGED = 'flagged', 'Flagged'

class ModerationAction(models.TextChoices):
    APPROVE = 'approve', 'Approve'
    REJECT = 'reject', 'Reject'
    FLAG = 'flag', 'Flag'

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
    thumbnail_url = models.URLField(blank=True)
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

    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
        db_index=True
    )
    moderation_notes = models.TextField(blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_projects'
    )
    rejection_reason = models.TextField(blank=True)

    currency = models.CharField(max_length=3, default="UAH")

    allow_overfunding = models.BooleanField(default=False)
    funded_at = models.DateTimeField(null=True, blank=True)
    
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
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_projects'
    )

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
        models.Index(fields=['moderation_status', 'created_at']),
        models.Index(fields=['is_deleted', 'moderation_status']),
    ]
    def __str__(self):
        return self.title

class ProjectAttachment(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    upload = models.ForeignKey("uploads.Upload", on_delete=models.CASCADE, default=None)   
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


class ProjectModerationLog(models.Model):
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='moderation_logs'
    )
    action = models.CharField(
        max_length=20,
        choices=ModerationAction.choices,
        help_text="Action performed"
    )
    moderator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderation_actions',
        help_text="Admin who performed the action"
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for the action"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes"
    )
    old_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="Previous moderation status"
    )
    new_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="New moderation status"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data (IP, user agent, etc.)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = 'project_moderation_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['moderator', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} on {self.project.title} by {self.moderator}"
