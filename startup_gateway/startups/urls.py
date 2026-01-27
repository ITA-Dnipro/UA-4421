from django.urls import path
from .views import StartupPublicDetailView

urlpatterns = [
    path('api/startups_wrong/<slug:slug>/', StartupPublicDetailView.as_view()),
]