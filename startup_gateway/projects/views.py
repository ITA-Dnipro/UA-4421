from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView, RetrieveAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
import csv
import logging
from io import StringIO
from django.http import HttpResponse
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination

from projects.models import Project, ProjectStatus, ProjectModerationLog, ModerationStatus
from projects.services.project_state_service import ProjectStateService
from projects.serializers import ProjectSerializer, ProjectDetailsSerializer, ProjectStateSerializer, \
    AdminProjectListSerializer, AdminProjectDetailSerializer, ModerationActionSerializer, ModerationLogSerializer, \
    BulkModerationSerializer
from projects.services.moderation_service import ProjectModerationService

from startups.models import StartupProfile
from .permissions import IsOwnerOrReadOnly, IsAdmin, IsAdminOrModerator

logger = logging.getLogger(__name__)


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

class AdminProjectPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProjectAdminFilter(filters.FilterSet):
    moderation_status = filters.ChoiceFilter(
        field_name='moderation_status',
        choices=ModerationStatus.choices
    )
    is_deleted = filters.BooleanFilter(field_name='is_deleted')
    startup_id = filters.NumberFilter(field_name='startup_profile__id')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = Project
        fields = [
            'moderation_status',
            'is_deleted',
            'startup_id',
            'status',
            'visibility',
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(startup_profile__company_name__icontains=value)
        )


class AdminProjectListView(ListAPIView):
    permission_classes = [IsAdminOrModerator]
    serializer_class = AdminProjectListSerializer
    pagination_class = AdminProjectPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProjectAdminFilter

    def get_queryset(self):
        queryset = Project.objects.select_related(
            'startup_profile',
            'startup_profile__user',
            'moderated_by'
        ).prefetch_related('tags').order_by('-created_at')

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(moderation_status=ModerationStatus.PENDING)),
            approved=Count('id', filter=Q(moderation_status=ModerationStatus.APPROVED)),
            rejected=Count('id', filter=Q(moderation_status=ModerationStatus.REJECTED)),
            flagged=Count('id', filter=Q(moderation_status=ModerationStatus.FLAGGED)),
            deleted=Count('id', filter=Q(is_deleted=True)),
        )

        response.data['stats'] = stats
        return response


class AdminProjectDetailView(RetrieveAPIView):
    permission_classes = [IsAdminOrModerator]
    serializer_class = AdminProjectDetailSerializer
    queryset = Project.objects.select_related(
        'startup_profile',
        'moderated_by',
        'deleted_by'
    ).prefetch_related('tags', 'moderation_logs')


class ProjectModerateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, id):
        project = get_object_or_404(Project, id=id)

        serializer = ModerationActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        notes = serializer.validated_data.get('notes', '')

        success, message, project = ProjectModerationService.moderate_project(
            project=project,
            action=action,
            moderator=request.user,
            reason=reason,
            notes=notes,
            request=request
        )

        if not success:
            return Response(
                {'detail': message},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AdminProjectDetailSerializer(project)
        return Response({
            'message': message,
            'project': serializer.data
        }, status=status.HTTP_200_OK)


class BulkModerationView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkModerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        project_ids = serializer.validated_data['project_ids']
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')

        projects = Project.objects.filter(id__in=project_ids)

        results = {
            'success': [],
            'failed': [],
            'total': len(project_ids)
        }

        for project in projects:
            success, message, _ = ProjectModerationService.moderate_project(
                project=project,
                action=action,
                moderator=request.user,
                reason=reason,
                notes='Bulk action',
                request=request
            )

            if success:
                results['success'].append({
                    'id': project.id,
                    'title': project.title
                })
            else:
                results['failed'].append({
                    'id': project.id,
                    'title': project.title,
                    'error': message
                })

        return Response(results, status=status.HTTP_200_OK)


class ModerationLogsView(ListAPIView):
    permission_classes = [IsAdminOrModerator]
    serializer_class = ModerationLogSerializer
    pagination_class = AdminProjectPagination

    def get_queryset(self):
        queryset = ProjectModerationLog.objects.select_related(
            'project',
            'moderator'
        ).order_by('-created_at')

        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        moderator_id = self.request.query_params.get('moderator_id')
        if moderator_id:
            queryset = queryset.filter(moderator_id=moderator_id)

        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        return queryset


class ExportProjectsCSVView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        filter_backend = ProjectAdminFilter(
            request.GET,
            queryset=Project.objects.select_related(
                'startup_profile',
                'moderated_by'
            ).all()
        )
        queryset = filter_backend.qs

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'ID',
            'Title',
            'Startup',
            'Owner Email',
            'Status',
            'Moderation Status',
            'Visibility',
            'Is Deleted',
            'Created At',
            'Moderated At',
            'Moderated By',
            'Target Amount',
            'Raised Amount',
        ])

        for project in queryset:
            writer.writerow([
                project.id,
                project.title,
                project.startup_profile.company_name,
                project.startup_profile.user.email,
                project.status,
                project.moderation_status,
                project.visibility,
                project.is_deleted,
                project.created_at.isoformat(),
                project.moderated_at.isoformat() if project.moderated_at else '',
                project.moderated_by.username if project.moderated_by else '',
                project.target_amount,
                project.raised_amount,
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response[
            'Content-Disposition'] = f'attachment; filename="projects_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        logger.info(f"Projects exported to CSV by {request.user.username}")

        return response
