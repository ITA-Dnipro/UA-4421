from django.urls import path

from .views import (
    ProjectRUDAPIView,
    ProjectStateServiceView,
    StartUpProjectsListCreateAPIView,
)

app_name = "projects"

urlpatterns = [
    path(
        "startups/<int:startup_id>/projects/",
        StartUpProjectsListCreateAPIView.as_view(),
        name="startup-projects",
    ),
    path("projects/<uuid:pk>/", ProjectRUDAPIView.as_view(), name="project-rud"),
    path(
        "projects/<uuid:pk>/status/",
        ProjectStateServiceView.as_view(),
        name="project-state-service",
    ),
]
