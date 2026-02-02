from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404

from startups.models import StartupProfile
from projects.models import Project
from .serializers import ProjectSummarySerializer

class ProjectPagination(PageNumberPagination):
    """Pagination for projects according to specification"""
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'results': data
        })

class ProjectFilter(filters.FilterSet):
    """Filter for startup projects"""
    status = filters.CharFilter(field_name='status', lookup_expr='exact')
    tag = filters.CharFilter(field_name='tags__name', lookup_expr='iexact')
    
    class Meta:
        model = Project
        fields = ['status', 'tag']

class StartupProjectsAPIView(ListAPIView):
    """
    API for retrieving projects of a specific startup
    GET /api/startups/{id}/projects/
    
    Returns projects for StartupProfile with specified ID
    """
    serializer_class = ProjectSummarySerializer
    pagination_class = ProjectPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProjectFilter
    
    def get_queryset(self):
        """
        Get queryset for this startup's projects
        Automatically filtered by startup ID and visibility
        """
        startup_id = self.kwargs['id']
        startup_profile = get_object_or_404(StartupProfile, id=startup_id)
        
        return startup_profile.projects.filter(
            visibility='public'
        ).order_by('-created_at')