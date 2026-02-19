from django.db import models
from django.conf import settings
from projects.models import Project


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

class Tracking(models.Model):
    id = models.UUIDField(primary_key=True)
    investor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracking')
    target_type = models.CharField(choices=(('startup','startup'),('project','project')))
    target_id = models.UUIDField()  # FK via generic relation or separate FK fields
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=32, null=True)  # 'manual','suggestion','import'
    meta = models.JSONField(null=True)  # optional metadata

    class Meta:
        unique_together = ('investor','target_type','target_id')
        indexes = [models.Index(fields=['investor']), models.Index(fields=['target_type','target_id'])]

class Investment(models.Model):
    id = models.UUIDField(primary_key=True)
    investor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='investments')
    status = models.CharField(choices=(('committed','committed'),('transferred','transferred'),('returned','returned'),('cancelled','cancelled')), default='committed')
    amount_committed = models.DecimalField(max_digits=18, decimal_places=2)
    amount_invested = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='UAH')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    meta = models.JSONField(null=True)  # notes, terms, round info

class PortfolioSnapshot(models.Model):
    id = models.UUIDField(primary_key=True)
    investor = models.ForeignKey(User, on_delete=models.CASCADE)
    computed_at = models.DateTimeField()
    projects_count = models.IntegerField()
    total_committed = models.DecimalField(max_digits=18, decimal_places=2)
    total_invested = models.DecimalField(max_digits=18, decimal_places=2)
    summary = models.JSONField()  # precomputed KPIs