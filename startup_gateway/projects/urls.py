from django.urls import path
from .views import (ProjectRUDAPIView, StartUpProjectsListCreateAPIView, ProjectStatusUpdateView, ProjectUpdateRaisedAmountView)

app_name = "projects"

urlpatterns = [
    path("startups/<int:startup_id>/projects/", StartUpProjectsListCreateAPIView.as_view(), name="startup-projects"),
    path("projects/<uuid:pk>/", ProjectRUDAPIView.as_view(), name="project-rud"),
    path("projects/<uuid:pk>/status/", ProjectStatusUpdateView.as_view(), name="project-status-update"),
    path("projects/<uuid:pk>/raised-amount/", ProjectUpdateRaisedAmountView.as_view(), name="update-raised-amount"),
]
