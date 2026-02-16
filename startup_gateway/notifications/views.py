from django.shortcuts import render
from rest_framework.generics import ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Notification
from .serializers import NotificationSerializer

class NotificationListAPIView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(user=self.request.user)
            .select_related("project")
            .order_by("-created_at")
        )

class NotificationMarkReadAPIView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    lookup_url_kwarg = "id"

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()

        if notification.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(status=status.HTTP_204_NO_CONTENT)
