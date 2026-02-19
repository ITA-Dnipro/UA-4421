from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from search.services import ProjectSearchService
from search.backends.meilisearch import MeiliSearchBackend
from projects.serializers import ProjectSerializer

class ProjectSearchAPIView(APIView):
    """
    GET /api/search/?q=keyword
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                required=True,
                type=OpenApiTypes.STR
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT, 
        },
        tags=['Search'] 
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"results": []})

        search_service = ProjectSearchService(backend=MeiliSearchBackend())
        results = search_service.search(query=query)

        return Response({"results": results}, status=status.HTTP_200_OK)
