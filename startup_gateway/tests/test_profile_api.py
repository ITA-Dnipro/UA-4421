import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


# ---------- Fixtures ----------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(
        username="owner",
        email="owner@test.com",
        password="password123",
        slug="owner-user",
        visibility=True,
        short_description="Owner profile",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other",
        email="other@test.com",
        password="password123",
        slug="other-user",
        visibility=True,
    )


# ---------- GET profile ----------

@pytest.mark.django_db
def test_public_profile_visible_to_anonymous(api_client, owner_user):
    owner_user.visibility = True
    owner_user.save()

    url = reverse("profile-detail", args=[owner_user.id])
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == owner_user.id


@pytest.mark.django_db
def test_hidden_profile_visible_to_owner(api_client, owner_user):
    owner_user.visibility = False
    owner_user.save()

    api_client.force_authenticate(user=owner_user)

    url = reverse("profile-detail", args=[owner_user.id])
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_hidden_profile_not_visible_to_anonymous(api_client, owner_user):
    owner_user.visibility = False
    owner_user.save()

    url = reverse("profile-detail", args=[owner_user.id])
    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_invalid_id_returns_404(api_client):
    url = reverse("profile-detail", args=[999999])
    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------- PATCH profile ----------

@pytest.mark.django_db
def test_owner_can_patch_profile(api_client, owner_user):
    api_client.force_authenticate(user=owner_user)

    url = reverse("profile-detail", args=[owner_user.id])
    payload = {
        "short_description": "Updated description",
        "visibility": False,
    }

    response = api_client.patch(url, payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["short_description"] == "Updated description"
    assert response.data["visibility"] is False


@pytest.mark.django_db
def test_non_owner_cannot_patch_profile(api_client, owner_user, other_user):
    api_client.force_authenticate(user=other_user)

    url = reverse("profile-detail", args=[owner_user.id])
    response = api_client.patch(
        url,
        {"short_description": "Hack attempt"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_duplicate_slug_returns_400(api_client, owner_user, other_user):
    api_client.force_authenticate(user=other_user)

    url = reverse("profile-detail", args=[other_user.id])
    response = api_client.patch(
        url,
        {"slug": owner_user.slug},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "slug" in response.data


# ---------- PUT profile ----------

@pytest.mark.django_db
def test_put_requires_all_required_fields(api_client, owner_user):
    api_client.force_authenticate(user=owner_user)

    url = reverse("profile-detail", args=[owner_user.id])
    response = api_client.put(
        url,
        {"short_description": "Only one field"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
