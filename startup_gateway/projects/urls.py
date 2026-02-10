from django.urls import path
<<<<<<< Updated upstream
from .views import (ProjectRUDAPIView, StartUpProjectsListCreateAPIView, ProjectStateServiceView, AdminProjectListView, ProjectModerateView)
=======
from .views import (ProjectRUDAPIView, StartUpProjectsListCreateAPIView, ProjectStateServiceView, ProjectAttachmentCreateAPIView)
>>>>>>> Stashed changes

app_name = "projects"

urlpatterns = [
    path("startups/<int:startup_id>/projects/", StartUpProjectsListCreateAPIView.as_view(), name="startup-projects"),
    path("projects/<uuid:pk>/", ProjectRUDAPIView.as_view(), name="project-rud"),
    path("projects/<uuid:pk>/status/", ProjectStateServiceView.as_view(), name="project-state-service"),
<<<<<<< Updated upstream
    path('admin/projects/', AdminProjectListView.as_view(), name='admin-project-list'),
    path('admin/projects/<uuid:id>/moderate/', ProjectModerateView.as_view(), name='admin-project-moderate'),
=======
    path("projects/attachments/create/", ProjectAttachmentCreateAPIView.as_view(), name="project-attachment-create"),
>>>>>>> Stashed changes
]
