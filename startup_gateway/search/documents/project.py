from projects.models import Project


class ProjectDocument:
    index = "projects"

    @staticmethod
    def from_instance(project: Project) -> dict:
        return {
            "id": str(project.id),
            "title": project.title,
            "short_description": project.short_description,
            "description": project.description,
            "startup_id": str(project.startup_profile.id),
            "startup_name": project.startup_profile.company_name,
            "tags": [tag.name for tag in project.tags.all()],
            "status": project.status,
            "thumbnail_url": project.thumbnail_url,
        }
