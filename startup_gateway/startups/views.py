from django.forms import ValidationError
from django.shortcuts import render
from rest_framework.generics import RetrieveAPIView, ListAPIView
from .models import StartupProfile
from .serializers import StartupPublicSerializer, StartupListSerializer, StartupPublishSerializer
from .permissions import CanPublishStartupProfile
from .services.startup_publish_service import publish_startup_profile
from rest_framework.views import APIView
from rest_framework.response import Response
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

class StartupPublishAPIView(APIView):
    permission_classes = [CanPublishStartupProfile]

    def post(self, request, pk=None):
        try:
            profile = StartupProfile.objects.get(uuid=pk)
        except StartupProfile.DoesNotExist:
            return Response({"detail": "Startup profile not found."}, status=404)

        self.check_object_permissions(request, profile)

        try:
            updated_profile = publish_startup_profile(profile, request.user)
        except ValidationError as e:
            return Response(e.detail, status=400)

        serializer = StartupPublishSerializer(updated_profile)
        return Response(serializer.data, status=200)