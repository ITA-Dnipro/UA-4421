from django.urls import path
from .views import StartupListView, StartupPublicDetailView, StartupProfileMeAPIView

urlpatterns = [
    path('api/startups/', StartupListView.as_view(), name='startup-list'),
    path('api/startups/me/', StartupProfileMeAPIView.as_view(), name='startup-profile-me'),
    path('api/startups/<slug:slug>/', StartupPublicDetailView.as_view(), name='startup-detail'),
]