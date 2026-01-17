from django.db import models
from users.models import User


class InvestorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='investor_profile'
    )
    company_name = models.CharField(max_length=255)
   
    class Meta:
        db_table = 'InvestorProfile'
        indexes = [
            models.Index(fields=['company_name']),
        ]

    def __str__(self):
        return self.company_name
