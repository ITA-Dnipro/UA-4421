from .base import SearchBackend


class PostgresSearchBackend(SearchBackend):
    def index(self, index: str, document: dict) -> None:
        # TODO: реалізувати через FTS / окрему таблицю
        pass

    def delete(self, index: str, document_id: str) -> None:
        # TODO: delete from search table
        pass

    def search(
        self,
        index: str,
        query: str,
        filters: dict | None = None,
    ) -> list[dict]:
        # TODO: SELECT ... WHERE tsvector @@ plainto_tsquery
        return []
