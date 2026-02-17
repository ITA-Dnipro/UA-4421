from django.urls import path
from .views import (ProjectRUDAPIView, StartUpProjectsListCreateAPIView, ProjectStateServiceView, AdminProjectListView, ProjectModerateView,
                     ProjectAttachmentCreateAPIView, ProjectHistoryView, ProjectRevertView)

app_name = "projects"

urlpatterns = [
    path("startups/<int:startup_id>/projects/", StartUpProjectsListCreateAPIView.as_view(), name="startup-projects"),
    path("projects/<uuid:pk>/", ProjectRUDAPIView.as_view(), name="project-rud"),
    path("projects/<uuid:pk>/status/", ProjectStateServiceView.as_view(), name="project-state-service"),
    path('admin/projects/', AdminProjectListView.as_view(), name='admin-project-list'),
    path('admin/projects/<uuid:id>/moderate/', ProjectModerateView.as_view(), name='admin-project-moderate'),
    path("projects/attachments/create/", ProjectAttachmentCreateAPIView.as_view(), name="project-attachment-create"),
    path ("projects/<uuid:pk>/history/", ProjectHistoryView.as_view(), name="project-history"),
    path ("projects/<uuid:pk>/revert/", ProjectRevertView.as_view(), name="project-revert"),
]
