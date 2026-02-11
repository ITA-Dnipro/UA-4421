from django.urls import path
from users.views import ProfileDetailUpdateView

urlpatterns = [
    path("profiles/<int:id>/", ProfileDetailUpdateView.as_view(), name="profile-detail"),
]