from django.db import models
from django.conf import settings


User = settings.AUTH_USER_MODEL


class InvestorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='investor_profile'
    )
    company_name = models.CharField(max_length=255)
   
    class Meta:
        db_table = 'investor_profiles'
        indexes = [
            models.Index(fields=['company_name']),
        ]

    def __str__(self):
        return self.company_name
