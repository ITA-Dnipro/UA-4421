from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import ProjectStatus

def update_raised_amount(project, new_amount):

    if not project.allow_overfunding and new_amount > project.target_amount:
         raise ValidationError(
            "Raised amount cannot exceed target amount unless overfunding is allowed."
        )
    
    project.raised_amount = new_amount
    
    if  project.status == ProjectStatus.FUNDRAISING and new_amount >= project.target_amount:
        project.status = ProjectStatus.FUNDED
        project.funded_at = timezone.now()

    project.save()
    return project