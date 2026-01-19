from django.db import models 

class SavedStartup(models.Model): 
    investor_profile = models.ForeignKey(
        'investors.InvestorProfile', 
        on_delete=models.CASCADE,
        related_name='saved_startups'
        ) 
    startup_profile = models.ForeignKey(
        'startups.StartupProfile', 
        on_delete=models.CASCADE,
        related_name='saved_by_investors'
        ) 
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta: 
        db_table = 'saved_startups'
        unique_together = ('investor_profile', 'startup_profile')

    def __str__(self):
        return f'{self.investor_profile} saved {self.startup_profile}'