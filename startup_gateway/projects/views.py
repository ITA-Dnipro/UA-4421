from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
import logging
from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination
from projects.models import Project, ModerationStatus
from projects.services.project_state_service import ProjectStateService
from projects.serializers import ProjectSerializer, ProjectDetailsSerializer, ProjectStateSerializer, \
    AdminProjectListSerializer, ModerationActionSerializer, ProjectAttachmentSerializer
from projects.services.moderation_service import ProjectModerationService
from startups.models import StartupProfile
from .permissions import  IsAdmin, IsAdminOrModerator, CanCreateProject, CanModifyProject

logger = logging.getLogger(__name__)


class StartUpProjectsListCreateAPIView(ListCreateAPIView):
    serializer_class = ProjectSerializer
    def get_permissions(self):
        if self.request.method == "POST":
            return [CanCreateProject()]
        return [AllowAny()]

    def get_queryset(self):
        startup_id = self.kwargs["startup_id"]
        qs = Project.objects.filter(startup_profile_id=startup_id, is_deleted=False)

        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return qs
            return qs.filter(Q(visibility="public") | Q(startup_profile__user=user))

        return qs.filter(visibility="public")

    def perform_create(self, serializer):
        startup = get_object_or_404(StartupProfile, id=self.kwargs["startup_id"])

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
    
    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [CanModifyProject()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Project.objects.filter(is_deleted=False)
        user = self.request.user

        if user.is_authenticated:
            if user.is_staff:
                return qs
            return qs.filter(Q(visibility="public") | Q(startup_profile__user=user))

        return qs.filter(visibility="public")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])

    
class ProjectStateServiceView(APIView):
    permission_classes = [CanModifyProject]

    def patch(self, request, pk):
        try:
            with transaction.atomic():

                project = Project.objects.select_for_update().get(
                    pk=pk,
                    is_deleted=False
                )
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

class AdminProjectPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProjectAdminFilter(filters.FilterSet):
    class Meta:
        model = Project
        fields = ['moderation_status', 'is_deleted']


class AdminProjectListView(ListAPIView):
    permission_classes = [IsAdminOrModerator]
    serializer_class = AdminProjectListSerializer
    pagination_class = AdminProjectPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProjectAdminFilter

    def get_queryset(self):
        return Project.objects.select_related(
            'startup_profile',
            'startup_profile__user',
            'moderated_by'
        ).prefetch_related('tags').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(moderation_status=ModerationStatus.PENDING)),
            approved=Count('id', filter=Q(moderation_status=ModerationStatus.APPROVED)),
            rejected=Count('id', filter=Q(moderation_status=ModerationStatus.REJECTED)),
            flagged=Count('id', filter=Q(moderation_status=ModerationStatus.FLAGGED)),
        )
        response.data['stats'] = stats
        return response


class ProjectModerateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, id):
        project = get_object_or_404(Project, id=id)

        serializer = ModerationActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        notes = serializer.validated_data.get('notes', '')

        success, message, project = ProjectModerationService.moderate_project(
            project=project,
            action=action,
            moderator=request.user,
            reason=reason,
            notes=notes
        )

        if not success:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': message,
            'project': AdminProjectListSerializer(project).data
        }, status=status.HTTP_200_OK)

class ProjectAttachmentCreateAPIView(APIView):
    serializer_class = ProjectAttachmentSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def post(self, request):
        serializer = ProjectAttachmentSerializer(data=request.data)
        if serializer.is_valid():
            attachment = serializer.save()
            return Response(ProjectAttachmentSerializer(attachment).data, status=201)
        return Response(serializer.errors, status=400)
