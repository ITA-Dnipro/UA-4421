from django.urls import path
from .views import StartupPublicDetailView

urlpatterns = [
    path('api/startups/<slug:slug>/', StartupPublicDetailView.as_view()),
]