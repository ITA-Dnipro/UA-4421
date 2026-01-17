from django.db import models
from projects.models import Project
from users.models import User

class Message(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Messages'
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f'Message from {self.sender} to {self.receiver}'
