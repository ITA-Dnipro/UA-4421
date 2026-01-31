from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from users.serializers import (
    PublicProfileSerializer,
    ProfileUpdateSerializer,
)
from users.permissions import IsOwnerOrReadOnly

User = get_user_model()


class ProfileDetailUpdateView(APIView):
    """
    GET    /api/profiles/{id}/      → public profile
    PATCH  /api/profiles/{id}/      → partial update (owner only)
    PUT    /api/profiles/{id}/      → full update (owner only)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        # PUT / PATCH
        return [
            IsAuthenticated(),
            IsOwnerOrReadOnly(),
        ]

    def get_object(self, id):
        return get_object_or_404(User, id=id)

    def get(self, request, id):
        user = self.get_object(id)

        if not user.visibility:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = PublicProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, id):
        user = self.get_object(id)
        self.check_object_permissions(request, user)

        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        user = self.get_object(id)
        self.check_object_permissions(request, user)

        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=False,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
