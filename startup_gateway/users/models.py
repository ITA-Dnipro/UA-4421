from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid 
from django.contrib.auth.models import UserManager
from django.utils.text import slugify

class CustomUserManager(UserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            username = uuid.uuid4().hex

        if "slug" not in extra_fields or not extra_fields.get("slug"):
            base = slugify(username)
            if not base:
                base = f"user-{uuid.uuid4().hex[:8]}"

            slug = base
            counter = 1
            while self.model.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1

            extra_fields["slug"] = slug

        return super().create_user(username, email, password, **extra_fields)
    
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

    objects = CustomUserManager()
    
    # --- core ---
    phone = models.CharField(max_length=20, blank=True)
    verified = models.BooleanField(default=False)
    email_verification_nonce = models.CharField(
        max_length=64,
        blank=True,
        default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # --- profile ---
    slug = models.SlugField(
        max_length=160,
        unique=True,
    )
    about_html = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    website = models.URLField(max_length=200, blank=True)
    media_urls = models.JSONField(default=list, blank=True)
    visibility = models.BooleanField(default=True)

    # --- relations ---
    roles = models.ManyToManyField(
        Role,
        through='UserRole',
        related_name='users'
    )

    tags = models.ManyToManyField(
        "projects.Tag",
        through="UserTag",
        related_name="users",
        blank=True
    )

    class Meta:
        db_table = 'users'

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

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE
    )
    tag = models.ForeignKey(
        "projects.Tag",
        on_delete=models.CASCADE
    )

    class Meta:
        db_table = "users_tags"
        unique_together = ("user", "tag")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["tag"]),
        ]

    def __str__(self):
        return f"{self.user.username} ↔ {self.tag.name}"


class PasswordResetAttempt(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='password_reset_attempts',
        help_text="User who requested reset (null if email not found)"
    )
    email = models.EmailField(
        db_index=True,
        help_text="Email address used in request"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address of requester"
    )
    token_sent = models.BooleanField(
        default=False,
        help_text="Whether reset token was actually sent"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = 'users_password_reset_attempts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        return f"Reset attempt: {self.email} at {self.created_at}"
