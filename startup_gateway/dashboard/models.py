from django.db import models 

class SavedStartap(models.Model): 
    investor_profile = models.ForeignKey(
        'investors.InvestorProfile', 
        on_delete=models.CASCADE,
        related_name='saved_startups'
        ) 
    startap_profile = models.ForeignKey(
        'startups.StartupProfile', 
        on_delete=models.CASCADE,
        related_name='saved_by_investors'
        ) 
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta: 
        db_table = 'SavedStartap'
        unique_together = ('investor_profile', 'startap_profile')

    def __str__(self):
        return f'{self.investor_profile} saved {self.startap_profile}'