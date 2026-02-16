from django.urls import path
from .views import StartupListView, StartupPublicDetailView, StartupPublishAPIView

urlpatterns = [
    path('api/startups/', StartupListView.as_view(), name='startup-list'),
    path('api/startups/<slug:slug>/', StartupPublicDetailView.as_view(), name='startup-detail'),
    path('api/profiles/<uuid:pk>/publish/', StartupPublishAPIView.as_view(), name='startup-publish'),
]