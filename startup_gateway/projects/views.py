from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from notifications.tasks import handle_project_event
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
import logging
from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination
from projects.models import Project, ModerationStatus
from django.utils.timezone import now
from projects.models import Project, ModerationStatus, ProjectAudit
from projects.services.project_state_service import ProjectStateService
from projects.serializers import ProjectSerializer, ProjectDetailsSerializer, ProjectStateSerializer, \
    AdminProjectListSerializer, ModerationActionSerializer, ProjectAttachmentSerializer, ProjectAuditSerializer
from projects.services.moderation_service import ProjectModerationService
from projects.services.audit_service import build_diff, serialize_value, AUDITABLE_FIELDS
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

        project = serializer.instance

        diff = {
            field: {"before": None, "after": serialize_value(getattr(project, field))}
            for field in AUDITABLE_FIELDS
        }
        ProjectAudit.objects.create(
            project=project,
            user=self.request.user,
            action='create',
            changes= diff
        )

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
    
    @transaction.atomic
    def perform_update(self, serializer):
        project = self.get_object()

        old_status = project.status
        updated_project = serializer.save()

        diff = build_diff(project, serializer.validated_data)
        if diff:
            ProjectAudit.objects.create(
                project=project,
                user=self.request.user,
                action='update',
                changes=diff
            )

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
    
    @transaction.atomic
    def perform_destroy(self, project):
        project = self.get_object()
        old_value = project.is_deleted
        project.is_deleted = True
        project.save(update_fields=["is_deleted"])

        diff = {"is_deleted": {"before": old_value, "after": project.is_deleted}}
        if diff:
            ProjectAudit.objects.create(
                project=project,
                user=self.request.user,
                action='delete',
                changes=diff
            )

    
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
                old_status = project.status

                serializer = ProjectStateSerializer(data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)

                state_service = ProjectStateService()

                project = state_service.update_project_state(
                    project=project,
                    data=serializer.validated_data,
                    user_is_staff=request.user.is_staff,
                    user=request.user  
                )           

                # Keep notifications consistent with PATCH /api/projects/{id}/
                if old_status != project.status:
                    transaction.on_commit(
                        lambda: handle_project_event.delay(
                            event_type="project_status_changed",
                            project_id=str(project.id),
                            payload={
                                "old_status": old_status,
                                "new_status": project.status,
                                "timestamp": now().isoformat(),
                            },
                        )
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
    permission_classes = [CanModifyProject]

    def post(self, request):
        serializer = ProjectAttachmentSerializer(data=request.data)
        if serializer.is_valid():
            attachment = serializer.save()
            return Response(ProjectAttachmentSerializer(attachment).data, status=201)
        return Response(serializer.errors, status=400)

class ProjectHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
class ProjectHistoryView(ListAPIView):
    serializer_class = ProjectAuditSerializer
    permission_classes = [CanModifyProject]
    pagination_class = ProjectHistoryPagination  

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs['pk'], is_deleted=False)

        self.check_object_permissions(self.request, project)

        return ProjectAudit.objects.filter(project=project).order_by('-created_at')
    

class ProjectRevertView(APIView):
    permission_classes = [CanModifyProject]

    @transaction.atomic
    def post(self, request, pk):
        project = Project.objects.select_for_update().get(pk=pk, is_deleted=False)
        if not project:
            return Response({"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        audit = ProjectAudit.objects.filter(project=project).order_by('-created_at').first()
        if not audit:
            return Response({"detail": "Audit entry not found"}, status=status.HTTP_404_NOT_FOUND)

        for field, values in audit.changes.items():
            if field in AUDITABLE_FIELDS:
                setattr(project, field, values["before"])

        project.save()

        ProjectAudit.objects.create(
            project=project,
            user=request.user,
            action="revert",
            changes=audit.changes
        )

        return Response(ProjectDetailsSerializer(project).data, status=status.HTTP_200_OK)