from django.urls import path
from .views import ProjectSearchAPIView

urlpatterns = [
    path("search/", ProjectSearchAPIView.as_view(), name="project-search"),
]
