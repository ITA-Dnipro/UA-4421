from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from rest_framework.views import APIView

from projects.models import Project
from projects.services.change_project_status import change_project_status
from projects.services.update_raised_amount import update_raised_amount
from projects.serializers import ProjectSerializer, ProjectDetailsSerializer, ProjectStatusUpdateSerializer, ProjectRaisedAmountUpdateSerializer

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

    
class ProjectStatusUpdateView(APIView):

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        serializer = ProjectStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            change_project_status(
                project,
                serializer.validated_data["status"],
                admin_override=request.user.is_staff
            )
        except ValidationError as e:
            return Response(
                {"detail": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"status": project.status})
    
class ProjectUpdateRaisedAmountView(APIView):

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        serializer = ProjectRaisedAmountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            update_raised_amount(
                project,
                serializer.validated_data["raised_amount"],
            )
        except ValidationError as e:
            return Response(
                {"detail": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"new_amount": project.raised_amount},
            status=status.HTTP_200_OK
        )
