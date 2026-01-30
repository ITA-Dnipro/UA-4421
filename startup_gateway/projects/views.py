from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework import status


from startups.models import StartupProfile
from .models import Project
from .serializers import ProjectSerializer, ProjectDetailsSerializer
from .permissions import IsOwnerOrReadOnly


class StartUpProjectsListCreateAPIView(ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        startup_id = self.kwargs["startup_id"]
        qs = Project.objects.filter(startup_profile_id=startup_id, is_deleted=False)

        user = self.request.user
        if user.is_authenticated:
            return qs.filter(Q(visibility="public") | Q(startup_profile__user=user))

        return qs.filter(visibility="public")

    def perform_create(self, serializer):
        startup = get_object_or_404(StartupProfile, id=self.kwargs["startup_id"])

        if startup.user != self.request.user:
            raise PermissionDenied("Only owner can create projects for this startup.")

        serializer.save(startup_profile=startup)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        project_id = serializer.instance.pk

        location = reverse("projects:project-rud", kwargs={"pk": project_id}, request=request)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers={"Location": location},
        )

class ProjectRUDAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectDetailsSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = Project.objects.filter(is_deleted=False)
        user = self.request.user

        if user.is_authenticated:
            return qs.filter(Q(visibility="public") | Q(startup_profile__user=user))

        return qs.filter(visibility="public")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])