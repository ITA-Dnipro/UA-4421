from django.urls import path

from .views import (ProjectStatusUpdateView)

urlpatterns = [
    path("projects/<uuid:pk>/status/", ProjectStatusUpdateView.as_view(), name="project-status-update"),

]
