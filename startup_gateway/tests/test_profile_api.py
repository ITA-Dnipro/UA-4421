import pytest
import re
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from users.services import generate_unique_slug

User = get_user_model()


# ========================================
# ---------- FIXTURES ----------
# ========================================
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


@pytest.fixture
def tags(db):
    from projects.models import Tag
    return [
        Tag.objects.create(name="python"),
        Tag.objects.create(name="django"),
    ]


# ========================================
# GET PROFILE TESTS
# ========================================
@pytest.mark.django_db
class TestGetProfile:

    def test_public_profile_visible_to_anonymous(self, api_client, owner_user):
        owner_user.visibility = True
        owner_user.save()
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == owner_user.id

    def test_hidden_profile_visible_to_owner(self, api_client, owner_user):
        owner_user.visibility = False
        owner_user.save()
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_hidden_profile_not_visible_to_anonymous(self, api_client, owner_user):
        owner_user.visibility = False
        owner_user.save()
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_id_returns_404(self, api_client):
        url = reverse("profile-detail", args=[999999])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ========================================
# PATCH PROFILE TESTS
# ========================================
@pytest.mark.django_db
class TestPatchProfile:

    @pytest.mark.parametrize("slug,value", [
        ("Max-1999", "max-1999"),
        ("another-TEST", "another-test"),
    ])
    def test_slug_lowercased(self, api_client, owner_user, slug, value):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"slug": slug, "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_200_OK
        owner_user.refresh_from_db()
        assert owner_user.slug == value

    @pytest.mark.parametrize("slug", ["", "№slug", "slug@", "slug!"])
    def test_slug_invalid(self, api_client, owner_user, slug):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"slug": slug, "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "slug" in response.data

    def test_slug_same_as_current(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"slug": owner_user.slug, "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_slug_duplicate_returns_400(self, api_client, owner_user, other_user):
        other_user.slug = "taken-slug"
        other_user.save()
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"slug": "taken-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "slug" in response.data

    def test_owner_can_patch_other_fields(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        payload = {"short_description": "Updated desc", "visibility": False}
        response = api_client.patch(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        owner_user.refresh_from_db()
        assert owner_user.short_description == "Updated desc"
        assert owner_user.visibility is False


# ========================================
# PUT PROFILE TESTS
# ========================================
@pytest.mark.django_db
class TestPutProfile:

    def test_put_requires_all_required_fields(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.put(url, {"short_description": "Only one field"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "slug" in response.data

    def test_put_all_fields_plus_extra(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        payload = {"slug": "new-slug", "short_description": "desc", "visibility": True, "extra": "ignored"}
        response = api_client.put(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        owner_user.refresh_from_db()
        assert owner_user.slug == "new-slug"


# ========================================
# MEDIA URLS TESTS
# ========================================
@pytest.mark.django_db
class TestProfileMediaUrls:

    @pytest.mark.parametrize("value", ["string", 123, True, {}])
    def test_media_urls_not_list(self, api_client, owner_user, value):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"media_urls": value, "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_media_urls_list_not_strings(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"media_urls": [123, True, {}], "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("url", ["ftp://example.com", "http:/example.com", "example.com"])
    def test_media_urls_invalid_url(self, api_client, owner_user, url):
        api_client.force_authenticate(user=owner_user)
        url_api = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url_api, {"media_urls": [url], "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_media_urls_valid(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url_api = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url_api, {"media_urls": ["https://example.com/image.png"], "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_200_OK


# ========================================
# CONTACTS TESTS
# ========================================
@pytest.mark.django_db
class TestProfileContacts:

    @pytest.mark.parametrize("value", ["string", [], 123, True])
    def test_contacts_not_dict(self, api_client, owner_user, value):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"contact": value, "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_contacts_invalid_keys(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"contact": {"facebook": "url"}, "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_contacts_valid(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"contact": {"email": "test@test.com", "telegram": "@nick"}, "slug": "test-slug", "short_description": "desc", "visibility": True}, format="json")
        assert response.status_code == status.HTTP_200_OK


# ========================================
# PATCH REQUIRED FIELDS TESTS
# ========================================
@pytest.mark.django_db
class TestProfilePatchRequiredFields:

    def test_patch_missing_required_fields(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        response = api_client.patch(url, {"slug": "only-slug"}, format="json")
        assert response.status_code == status.HTTP_200_OK


# ========================================
# SLUG SERVICE TESTS
# ========================================
@pytest.mark.django_db
class TestSlugService:

    def test_generate_slug_fallback(self):
        user = User(username="!!!")
        slug = generate_unique_slug(user)
        assert re.match(r"user-[a-f0-9]{8}", slug)

    def test_generate_slug_increment(self):
        User.objects.create(username="test0", slug="test")
        User.objects.create(username="test", slug="")
        user = User(username="test")
        slug = generate_unique_slug(user)
        assert slug == "test-1"


# ========================================
# TAGS TESTS
# ========================================
@pytest.mark.django_db
class TestProfileTags:

    def test_add_valid_tags(self, api_client, owner_user, tags):        
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        
        response = api_client.patch(
            url,
            {"tags": [tags[0].id, tags[1].id]},
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["tags"]) == 2

    def test_invalid_tag_id_returns_400(self, api_client, owner_user):        
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        
        response = api_client.patch(
            url,
            {"tags": [999999]},
            format="json"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "tags" in response.data

    def test_tags_not_list_returns_400(self, api_client, owner_user):        
        api_client.force_authenticate(user=owner_user)
        url = reverse("profile-detail", args=[owner_user.id])
        
        response = api_client.patch(
            url,
            {"tags": "not-a-list"},
            format="json"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
