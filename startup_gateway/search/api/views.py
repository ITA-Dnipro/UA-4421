from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from search.services import ProjectSearchService
from search.backends.meilisearch import MeiliSearchBackend


class ProjectSearchAPIView(APIView):
    """
    GET /api/search/?q=keyword
    """
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"results": []})

        search_service = ProjectSearchService(backend=MeiliSearchBackend())
        results = search_service.search_projects(query=query)

        return Response({"results": results}, status=status.HTTP_200_OK)
