from django.urls import path
from .views import (ProjectRUDAPIView, StartUpProjectsListCreateAPIView, ProjectStateServiceView, AdminProjectListView, AdminProjectDetailView, ProjectModerateView, BulkModerationView, ModerationLogsView, ExportProjectsCSVView)

app_name = "projects"

urlpatterns = [
    path("startups/<int:startup_id>/projects/", StartUpProjectsListCreateAPIView.as_view(), name="startup-projects"),
    path("projects/<uuid:pk>/", ProjectRUDAPIView.as_view(), name="project-rud"),
    path("projects/<uuid:pk>/status/", ProjectStateServiceView.as_view(), name="project-state-service"),
    path('admin/projects/', AdminProjectListView.as_view(), name='admin-project-list'),
    path('admin/projects/<uuid:pk>/', AdminProjectDetailView.as_view(), name='admin-project-detail'),
    path('admin/projects/<uuid:id>/moderate/', ProjectModerateView.as_view(), name='admin-project-moderate'),
    path('admin/projects/bulk-moderate/', BulkModerationView.as_view(), name='admin-bulk-moderate'),
    path('admin/projects/moderation-logs/', ModerationLogsView.as_view(), name='admin-moderation-logs'),
    path('admin/projects/export/', ExportProjectsCSVView.as_view(), name='admin-export-projects'),
]
