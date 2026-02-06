from meilisearch import Client
from search.backends.base import SearchBackend


class MeiliSearchBackend(SearchBackend):
    def __init__(self):
        self.client = Client(
            "http://meilisearch:7700", 
            "masterKey"
        )

    def index(self, index_name: str, document: dict) -> None:
        if not self.index_exists(index_name):
            self.create_index(index_name)
        self.client.index(index_name).add_documents([document])

    def delete(self, index_name: str, document_id: str) -> None:
        self.client.index(index_name).delete_document(document_id)

    def search(self, index_name: str, query: str, filters=None) -> list[dict]:
        search_params = {}
        if filters:
            search_params['filter'] = filters
            
        result = self.client.index(index_name).search(query, search_params)
        return result["hits"]
    
    def index_exists(self, index_name: str) -> bool:
        try:
            self.client.get_index(index_name)
            return True
        except Exception:
            return False

    def create_index(self, index_name: str):
         self.client.create_index(uid=index_name, options={"primaryKey": "id"})