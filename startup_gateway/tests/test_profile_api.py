import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(
        username="owner_user",
        email="owner@test.com",
        password="password123",
        short_description="Old description",
        visibility=True,
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other_user",
        email="other@test.com",
        password="password123",
    )


@pytest.mark.django_db
def test_get_public_profile(api_client, owner_user):
    response = api_client.get(f"/api/profiles/{owner_user.id}/")

    assert response.status_code == 200
    data = response.json()

    assert data["username"] == owner_user.username
    assert "stats" in data
    assert "projects_count" in data["stats"]


@pytest.mark.django_db
def test_owner_can_patch_profile(api_client, owner_user):
    api_client.force_authenticate(user=owner_user)

    response = api_client.patch(
        f"/api/profiles/{owner_user.id}/",
        {
            "short_description": "Updated description",
            "visibility": False,
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()

    assert data["short_description"] == "Updated description"
    assert data["visibility"] is False


@pytest.mark.django_db
def test_non_owner_cannot_update(api_client, owner_user, other_user):
    api_client.force_authenticate(user=other_user)

    response = api_client.patch(
        f"/api/profiles/{owner_user.id}/",
        {"short_description": "Hack attempt"},
        format="json",
    )

    assert response.status_code == 403
