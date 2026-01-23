from django.urls import path

from .views import landing_content

urlpatterns = [
    path("api/content/landing/", landing_content, name="landing-content"),
]
