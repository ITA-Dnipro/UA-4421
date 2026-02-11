from search.backends.base import SearchBackend
from search.documents.project import ProjectDocument
from projects.models import Project


class ProjectSearchService:
    def __init__(self, backend: SearchBackend):
        self.backend = backend

    def index_project(self, project: Project) -> None:
        document = ProjectDocument.from_instance(project)
        self.backend.index(ProjectDocument.index, document)

    def remove_project(self, project: Project) -> None:
        self.backend.delete(ProjectDocument.index, str(project.id))

    def search(self, query: str, filters: dict | None = None) -> list[dict]:
        return self.backend.search(
            ProjectDocument.index,
            query,
            filters=filters,
        )
