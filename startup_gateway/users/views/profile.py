from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from users.serializers import PublicProfileSerializer, ProfileUpdateSerializer
from users.permissions import IsOwnerOrReadOnly

User = get_user_model()


class ProfileDetailUpdateView(APIView):
    permission_classes = [IsOwnerOrReadOnly]

    def get_object(self, id):
        return User.objects.get(id=id)

    def get(self, request, id):
        user = self.get_object(id)
        serializer = PublicProfileSerializer(user)
        return Response(serializer.data)

    def patch(self, request, id):
        user = self.get_object(id)
        self.check_object_permissions(request, user)

        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def put(self, request, id):
        user = self.get_object(id)
        self.check_object_permissions(request, user)

        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=False
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
