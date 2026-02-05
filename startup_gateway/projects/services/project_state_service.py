from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import ProjectStatus, ProjectVisibility
from search.services import ProjectSearchService
from search.backends.meilisearch import MeiliSearchBackend

ALLOWED_STATUS_TRANSITIONS = {
    ProjectStatus.IDEA: {ProjectStatus.MVP},
    ProjectStatus.MVP: {ProjectStatus.FUNDRAISING},
    ProjectStatus.FUNDRAISING: {ProjectStatus.FUNDED},
    ProjectStatus.FUNDED: {ProjectStatus.CLOSED},
    ProjectStatus.CLOSED: set(),
}

class ProjectStateService:

    def __init__(self, search_service: ProjectSearchService | None = None):
        self.search_service = search_service or ProjectSearchService(
            backend=MeiliSearchBackend()
        )
    
    def update_project_state(self, project, data, user_is_staff=False):

        if "raised_amount" in data:
            self.set_raised_amount(project, data["raised_amount"])

        if "status" in data:
            self.change_status(project, data["status"], admin_override=user_is_staff)

        if "visibility" in data:
            self.change_visibility(project, data["visibility"])

        project.save()
        return project

    def set_raised_amount(self, project, new_amount):
        if new_amount < 0:
            raise ValidationError("Raised amount cannot be negative")
        
        if new_amount > project.target_amount and not project.allow_overfunding:
            raise ValidationError("Overfunding is not allowed.")

        project.raised_amount = new_amount
        
        if project.raised_amount >= project.target_amount and project.status == ProjectStatus.FUNDRAISING:
            self.change_status(project, ProjectStatus.FUNDED)

    def change_status(self, project, new_status, admin_override=False):
        if project.status == new_status:
            return

        if not admin_override:
            allowed = ALLOWED_STATUS_TRANSITIONS.get(project.status, set())
            if new_status not in allowed:
                raise ValidationError(f"Transition {project.status} -> {new_status} not allowed")

        if new_status == ProjectStatus.FUNDED and project.raised_amount < project.target_amount:
            raise ValidationError("Target amount not reached yet.")

        project.status = new_status
        if new_status == ProjectStatus.FUNDED and not project.funded_at:
            project.funded_at = timezone.now()

    def change_visibility(self, project, new_visibility):
        old_visibility = project.visibility
        project.visibility = new_visibility

        if (
            old_visibility != ProjectVisibility.PUBLIC
            and new_visibility == ProjectVisibility.PUBLIC
        ):
            self.index_project_in_search(project)

        if (
            old_visibility == ProjectVisibility.PUBLIC
            and new_visibility != ProjectVisibility.PUBLIC
        ):
            self.remove_project_from_search(project)

    def index_project_in_search(self, project):
        self.search_service.index_project(project)

    def remove_project_from_search(self, project):
        self.search_service.remove_project(project)

        