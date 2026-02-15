from django.shortcuts import render
from rest_framework.generics import RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from .models import StartupProfile
from .serializers import StartupPublicSerializer, StartupListSerializer, StartupProfileMeSerializer
from .pagination import StartupListPagination


# Create your views here.
class StartupPublicDetailView(RetrieveAPIView):
    queryset = (
        StartupProfile.objects
        .prefetch_related('projects__tags')
    )
    serializer_class = StartupPublicSerializer
    lookup_field = 'slug'

class StartupListView(ListAPIView):
    serializer_class = StartupListSerializer
    pagination_class = StartupListPagination

    def get_queryset(self):
        queryset = StartupProfile.objects.all().prefetch_related('projects__tags', 'region').order_by("-id")

        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(projects__tags__name__iexact=tag).distinct()

        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(company_name__icontains=search)

        return queryset
    
class StartupProfileMeAPIView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StartupProfileMeSerializer

    def get_object(self):
        user = self.request.user
        
        try:
            return StartupProfile.objects.get(user=user)
        except StartupProfile.DoesNotExist:
            raise NotFound("Startup profile not found.")