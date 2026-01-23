from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.shortcuts import get_object_or_404

from startups.models import StartupProfile
from projects.models import Project
from .serializers import ProjectSummarySerializer

class ProjectPagination(PageNumberPagination):
    """Пагінація для проектів згідно специфікації"""
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'results': data
        })

class StartupProjectsAPIView(APIView):
    """
    API для отримання проектів конкретного стартапу
    GET /api/startups/{id}/projects/
    
    Повертає проекти для StartupProfile з вказаним ID
    """
    
    pagination_class = ProjectPagination
    
    def get(self, request, id):
        """
        Отримати проекти стартапу з пагінацією
        
        Query параметри:
        - page (int, optional): номер сторінки, default=1
        - page_size (int, optional): елементів на сторінку, default=6
        - status (str, optional): фільтр за статусом проекту
        - tag (str, optional): фільтр за тегом
        """
        try:
            # 1. Знаходимо стартап по ID
            startup_profile = get_object_or_404(StartupProfile, id=id)
            
            # 2. Отримуємо проекти цього стартапу
            queryset = startup_profile.projects.all()
            
            # 3. Фільтрація за статусом (опційно)
            status_param = request.query_params.get('status')
            if status_param:
                queryset = queryset.filter(status=status_param)
            
            # 4. Фільтрація за тегом (опційно)
            tag_param = request.query_params.get('tag')
            if tag_param:
                queryset = queryset.filter(tags__name__iexact=tag_param)
            
            # 5. Показуємо тільки публічні проекти за замовчуванням
            queryset = queryset.filter(visibility='public')
            
            # 6. Сортуємо за датою створення (новіші першими)
            queryset = queryset.order_by('-created_at')
            
            # 7. Застосовуємо пагінацію
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            
            # 8. Серіалізуємо дані
            serializer = ProjectSummarySerializer(
                paginated_queryset,
                many=True,
                context={'request': request}
            )
            
            # 9. Повертаємо відповідь згідно специфікації
            return paginator.get_paginated_response(serializer.data)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in StartupProjectsAPIView: {str(e)}")
            
            return Response(
                {
                    'error': 'Failed to fetch startup projects',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )