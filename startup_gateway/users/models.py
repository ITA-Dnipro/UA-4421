from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import uuid

class Role(models.Model):
    """
    Roles: 'startup', 'investor'.
    """

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    AbstractUser for:
    - username
    - first_name
    - last_name
    - email
    - password
    """

    phone = models.CharField(max_length=20, blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    slug = models.SlugField(unique=True, blank=True)
    about_html = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    website = models.URLField(max_length=200, blank=True)    
    media_urls = models.JSONField(default=list, blank=True)
    visibility = models.BooleanField(default=True)

    # relationship with tags defined in projects.models.Tag
    tags = models.ManyToManyField(
        "projects.Tag",   # reference to a model from another app
        through="UserTag",
        related_name="users",
        blank=True
    )

    roles = models.ManyToManyField(
        Role,
        through='UserRole',
        related_name='users'
    )

    class Meta:
        db_table = 'users'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.username)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class UserRole(models.Model):
    """
    Звʼязок user ↔ role (many-to-many).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_roles'
        unique_together = ('user', 'role')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"
        
class UserTag(models.Model):
    """
    Intermediate table for linking User ↔ Tag (many-to-many).
    """
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    tag = models.ForeignKey("projects.Tag", on_delete=models.CASCADE)

    class Meta:
        db_table = "users_tags"
        unique_together = ("user", "tag")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["tag"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} ↔ {self.tag.name}"