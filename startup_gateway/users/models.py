from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.Model):
    """
    Ролі: 'startup', 'investor'.
    """

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'Roles'

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    AbstractUser для стандартних полів:
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
        db_table = 'Users'

    def __str__(self):
        return self.username


class UserRole(models.Model):
    """
    Звʼязок user ↔ role (many-to-many).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        db_table = 'UserRoles'
        unique_together = ('user', 'role')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"
