from django.urls import path
from .views import StartupPublicDetailView

urlpatterns = [
    path('api/startups/<int:pk>/', StartupPublicDetailView.as_view()),
]