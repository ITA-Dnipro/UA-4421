from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from notifications.tasks import handle_project_event
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from django.utils.timezone import now

from projects.models import Project, ProjectStatus
from projects.services.project_state_service import ProjectStateService
from projects.serializers import ProjectSerializer, ProjectDetailsSerializer, ProjectStateSerializer

from startups.models import StartupProfile
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

        project = serializer.instance

        handle_project_event.delay(
            event_type="project_created",
            project_id=str(project.id),
            payload={
                "title": project.title,
                "status": project.status,
            },
        )

        location = reverse("projects:project-rud", kwargs={"pk": project.id}, request=request)

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

    def perform_update(self, serializer):
        project = self.get_object()
        old_status = project.status
        updated_project = serializer.save()

        if (
            "status" in serializer.validated_data
            and old_status != updated_project.status
        ):
            handle_project_event.delay(
            event_type="project_status_changed",
            project_id=str(updated_project.id),
            payload={
                "old_status": old_status,
                "new_status": updated_project.status,
                "timestamp": now().isoformat(),
            },
        )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])

    
class ProjectStateServiceView(APIView):
    permission_classes = [IsOwnerOrReadOnly]

    def patch(self, request, pk):
        try:
            with transaction.atomic():

                project = Project.objects.select_for_update().get(pk=pk)
                self.check_object_permissions(request, project)

                serializer = ProjectStateSerializer(data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)

                state_service = ProjectStateService()
                
                project = state_service.update_project_state(
                    project=project,
                    data=serializer.validated_data,
                    user_is_staff=request.user.is_staff
                )

        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except Project.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(ProjectDetailsSerializer(project).data)