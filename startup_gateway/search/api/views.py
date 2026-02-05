from rest_framework.views import APIView
from rest_framework.response import Response

from search.backends.postgres import PostgresSearchBackend
from search.services import ProjectSearchService


class SearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")

        service = ProjectSearchService(
            backend=PostgresSearchBackend()
        )

        results = service.search(query)
        return Response(results)
