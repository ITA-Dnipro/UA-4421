from meilisearch import Client
from search.backends.base import SearchBackend


class MeiliSearchBackend(SearchBackend):
    def __init__(self):
        self.client = Client(
            "http://meilisearch:7700",
            "masterKey"
        )
        self.index = self.client.index("projects")

    def index(self, index: str, document: dict) -> None:
        self.index.add_documents([document])

    def delete(self, index: str, document_id: str) -> None:
        self.index.delete_document(document_id)

    def search(self, index: str, query: str, filters=None) -> list[dict]:
        result = self.index.search(query, filters=filters)
        return result["hits"]