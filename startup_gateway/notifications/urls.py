from django.urls import path

from .views import (
    NotificationListAPIView,
    NotificationMarkReadAPIView,
)

app_name = "notifications"

urlpatterns = [
    # GET /api/notifications/
    path(
        "",
        NotificationListAPIView.as_view(),
        name="notification-list",
    ),

    # PATCH /api/notifications/{id}/read/
    path(
        "<int:id>/read/",
        NotificationMarkReadAPIView.as_view(),
        name="notification-mark-read",
    ),
]
