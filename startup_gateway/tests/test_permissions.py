import pytest
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from users.permissions import IsOwnerOrReadOnly

User = get_user_model()


@pytest.mark.django_db
class TestIsOwnerOrReadOnly:

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.permission = IsOwnerOrReadOnly()

    def test_safe_method_allows_anyone(self):
        request = self.factory.get("/fake/")
        request.user = None
        obj = User(username="test")

        assert self.permission.has_object_permission(
            request, None, obj
        ) is True

    def test_owner_can_write(self):
        user = User.objects.create_user(username="owner", password="123")
        request = self.factory.patch("/fake/")
        request.user = user

        assert self.permission.has_object_permission(
            request, None, user
        ) is True

    def test_authenticated_not_owner_cannot_write(self):
        owner = User.objects.create_user(username="owner", password="123")
        other = User.objects.create_user(username="other", password="123")

        request = self.factory.patch("/fake/")
        request.user = other

        assert self.permission.has_object_permission(
            request, None, owner
        ) is False

    def test_anonymous_cannot_write(self):
        owner = User.objects.create_user(username="owner", password="123")

        request = self.factory.patch("/fake/")
        request.user = type("Anonymous", (), {"is_authenticated": False})()

        assert self.permission.has_object_permission(
            request, None, owner
        ) is False
