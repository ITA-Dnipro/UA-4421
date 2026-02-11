from django.db import models
from django.contrib.auth.models import AbstractUser
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

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )

    phone = models.CharField(max_length=20, blank=True)
    verified = models.BooleanField(default=False)
    email_verification_nonce = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    jwt_version = models.IntegerField(
        default=0,
        help_text="Incremented on password change to invalidate existing JWT tokens"
    )

    roles = models.ManyToManyField(
        Role,
        through='UserRole',
        related_name='users'
    )

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username
    
    def is_startup(self) -> bool:
        return (
            hasattr(self, "startup_profile") or
            self.roles.filter(name__iexact="startup").exists()
        )


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


class PasswordResetConfirmation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_confirmations',
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address where password reset was attempted"
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether password reset was successful"
    )
    failure_reason = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Internal categorization of failure (not exposed to users)",
        choices=[
            ('invalid_uid_format', 'Invalid UID Format'),
            ('invalid_uid_or_user', 'Invalid UID or User Not Found'),
            ('invalid_token', 'Invalid or Expired Token'),
            ('weak_password', 'Weak Password'),
            ('validation_error', 'Other Validation Error'),
        ]
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = 'users_password_reset_confirmations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]

    def __str__(self):
        status = "successful" if self.success else f"failed ({self.failure_reason})"
        user_info = self.user.username if self.user else "unknown user"
        return f"Password reset {status} for {user_info} at {self.created_at}"
