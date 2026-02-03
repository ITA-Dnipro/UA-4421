from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import ProjectStatus, ProjectVisibility


ALLOWED_STATUS_TRANSITIONS = {
    ProjectStatus.IDEA: {ProjectStatus.MVP},
    ProjectStatus.MVP: {ProjectStatus.FUNDRAISING},
    ProjectStatus.FUNDRAISING: {ProjectStatus.FUNDED},
    ProjectStatus.FUNDED: {ProjectStatus.CLOSED},
    ProjectStatus.CLOSED: set(),
}

class ProjectStateService:

    def change_status(self,project, new_status, *, admin_override=False):
        current_status = project.status
        
        if new_status == ProjectStatus.FUNDED and not admin_override:
            if current_status != ProjectStatus.FUNDRAISING:
                raise ValidationError("FUNDED status can only be set from FUNDRAISING projects")
            if project.raised_amount < project.target_amount:
                raise ValidationError("FUNDED status can only be set when raised_amount >= target_amount")

        if not admin_override:
            allowed_status = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
            if new_status not in allowed_status:
                raise ValidationError(
                    f"Invalid status transition: {current_status} → {new_status}"
                )
        project.status = new_status

        if new_status == ProjectStatus.FUNDED and project.funded_at is None:
            project.funded_at = timezone.now()

        project.save(update_fields=["status", "funded_at"])
        return project

    def set_raised_amount(self, project, new_amount):
        if new_amount < 0:
            raise ValidationError("Raised amount cannot be negative")

        if new_amount > project.target_amount and not project.allow_overfunding:
            raise ValidationError("Raised amount cannot exceed target amount unless overfunding is allowed.")

        project.raised_amount = new_amount

        if project.raised_amount >= project.target_amount and project.status == ProjectStatus.FUNDRAISING:
            self.change_status(project, ProjectStatus.FUNDED)

        project.save(update_fields=["raised_amount", "status", "funded_at"])
        return project
    
    def change_visibility(self, project, new_visibility):

        project.visibility = new_visibility
        project.save(update_fields=["visibility"])

        if new_visibility == ProjectVisibility.PUBLIC and not project.is_indexed:
            self.index_project_in_search(project)
            project.is_indexed = True
            project.save(update_fields=["is_indexed"])

        return project
    
    def index_project_in_search(self, project):
        # Temporary plug so that tests don't fail
        print(f"[TEST] Indexing project {project.id} in search")

        