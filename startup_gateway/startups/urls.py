from django.urls import path
from .views import StartupListView, StartupPublicDetailView

urlpatterns = [
    path('api/startups/', StartupListView.as_view(), name='startup-list'),
    path('api/startups/<slug:slug>/', StartupPublicDetailView.as_view(), name='startup-detail'),
]