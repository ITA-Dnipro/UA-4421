from abc import ABC, abstractmethod


class SearchBackend(ABC):
    @abstractmethod
    def index(self, index: str, document: dict) -> None:
        pass

    @abstractmethod
    def delete(self, index: str, document_id: str) -> None:
        pass

    @abstractmethod
    def search(
        self,
        index: str,
        query: str,
        filters: dict | None = None,
    ) -> list[dict]:
        pass
