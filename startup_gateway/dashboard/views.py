from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from dashboard.models import SavedItem
from dashboard.serializers import SavedItemCreateSerializer


class SavedItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id != int(user_id):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SavedItemCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        investor = serializer.validated_data["investor"]
        ct = serializer.validated_data["content_type"]
        object_id = serializer.validated_data["target_id_str"]

        saved, created = SavedItem.objects.get_or_create(
            investor_profile=investor,
            content_type=ct,
            object_id=object_id,
        )

        payload = {
            "saved_id": saved.id,
            "saved_at": saved.created_at.isoformat(),
        }
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, user_id, saved_id):
        if request.user.id != int(user_id):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        saved = get_object_or_404(SavedItem, id=saved_id, investor_profile__user=request.user)
        saved.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
