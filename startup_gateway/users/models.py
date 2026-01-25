from django.db import models
from django.contrib.auth.models import AbstractUser

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

    roles = models.ManyToManyField(
        Role,
        through='UserRole',
        related_name='users'
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
