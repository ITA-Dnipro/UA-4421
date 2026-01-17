from django.db import models 
from startups.models import StartupProfile 
from investors.models import InvestorProfile 


class SavedStartap(models.Model): 
    investor_profile = models.ForeignKey(
        InvestorProfile, 
        on_delete=models.CASCADE,
        related_name='saved_startups'
        ) 
    startap_profile = models.ForeignKey(
        StartupProfile, 
        on_delete=models.CASCADE,
        related_name='saved_by_investors'
        ) 
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta: 
        db_table = 'SavedStartap'
        unique_together = ('investor', 'startup')

    def __str__(self):
        return f'{self.investor_profile} saved {self.startap_profile}'