from projects.models import Project


class ProjectDocument:
    index = "projects"

    @staticmethod
    def from_instance(project: Project) -> dict:
        return {
            "id": str(project.id),
            "title": project.title or "",
            "short_description": project.short_description or "",
            "description": project.description or "",
            "location": getattr(project, "location", "") or "",
            "startup_id": str(project.startup_profile.id) if project.startup_profile else "",
            "startup_name": project.startup_profile.company_name if project.startup_profile else "",
            "visibility": project.visibility or "public",
            "tags": [tag.name for tag in project.tags.all()],
            "status": project.status or "",
            "thumbnail_url": project.thumbnail_url or "",
        }
