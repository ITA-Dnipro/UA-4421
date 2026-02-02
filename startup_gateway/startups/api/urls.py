from django.urls import path
from .views import StartupProjectsAPIView

app_name = 'startups_api'

urlpatterns = [
    path(
        'startups/<int:id>/projects/public/',
        StartupProjectsAPIView.as_view(),
        name='public-projects'
    ),
]