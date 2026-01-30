from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import ProjectStatus


ALLOWED_STATUS_TRANSITIONS = {
    ProjectStatus.IDEA: {ProjectStatus.MVP},
    ProjectStatus.MVP: {ProjectStatus.FUNDRAISING},
    ProjectStatus.FUNDRAISING: {ProjectStatus.FUNDED},
    ProjectStatus.FUNDED: {ProjectStatus.CLOSED},
    ProjectStatus.CLOSED: set(),
}

def change_project_status(project, new_status, *, admin_override=False):
    current_status = project.status

    if not admin_override:
        alloved_status = ALLOWED_STATUS_TRANSITIONS.get(current_status)
        if new_status not in alloved_status:
            raise ValidationError(
                f"Invalid status transition: {current_status} → {new_status}"
            )
    project.status = new_status

    if new_status == ProjectStatus.FUNDED and project.funded_at is None:
        project.funded_at = timezone.now()

    project.save(update_fields=["status", "funded_at"])
    return project
