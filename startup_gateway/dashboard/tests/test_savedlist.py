import uuid
import pytest
from rest_framework.test import APIClient
from django.contrib.contenttypes.models import ContentType
from users.models import User, Role
from investors.models import InvestorProfile
from startups.models import StartupProfile
from projects.models import Project, Tag
from dashboard.models import SavedItem


@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def investor_user(db):
    user = User.objects.create_user(username="inv", password="pass")
    InvestorProfile.objects.create(user=user)
    return user

@pytest.fixture
def auth_client(api_client, investor_user):
    api_client.force_authenticate(investor_user)
    return api_client

@pytest.fixture
def startup_with_projects(db):
    user = User.objects.create_user(username="startup", password="pass")
    startup = StartupProfile.objects.create(
        user=user,
        company_name="Test Startup",
        slug="test-startup"
    )

    tag1 = Tag.objects.create(name="ai")
    tag2 = Tag.objects.create(name="fintech")

    p1 = Project.objects.create(
        startup_profile=startup,
        title="P1",
        slug="p1",
        short_description="s",
        description="d",
        target_amount=100
    )
    p1.tags.add(tag1)

    p2 = Project.objects.create(
        startup_profile=startup,
        title="P2",
        slug="p2",
        short_description="s",
        description="d",
        target_amount=200
    )
    p2.tags.add(tag2)

    return startup, user, [tag1.name, tag2.name]

def test_list_saved_startup_tags_aggregated(
    auth_client, investor_user, startup_with_projects
):
    startup, startup_user, tag_names = startup_with_projects

    SavedItem.objects.create(
        investor_profile=investor_user.investor_profile,
        content_type=ContentType.objects.get_for_model(StartupProfile),
        object_id=startup.uuid
    )

    url = f"/api/users/{investor_user.id}/saved/"
    r = auth_client.get(url)

    assert r.status_code == 200
    assert r.data["count"] == 1

    item = r.data["results"][0]
    assert set(item["tags"]) == set(tag_names)
    assert item["type"] == "startup"

def test_list_saved_project_tags(auth_client, investor_user, startup_with_projects):
    startup, _, tag_names = startup_with_projects
    project = startup.projects.first()

    SavedItem.objects.create(
        investor_profile=investor_user.investor_profile,
        content_type=ContentType.objects.get_for_model(Project),
        object_id=project.id
    )

    r = auth_client.get(f"/api/users/{investor_user.id}/saved/")
    item = r.data["results"][0]

    assert item["tags"] == [project.tags.first().name]
    assert item["type"] == "project"

def test_type_filter_project_only(auth_client, investor_user, startup_with_projects):
    startup, _, _ = startup_with_projects
    project = startup.projects.first()

    SavedItem.objects.create(
        investor_profile=investor_user.investor_profile,
        content_type=ContentType.objects.get_for_model(Project),
        object_id=project.id
    )

    SavedItem.objects.create(
        investor_profile=investor_user.investor_profile,
        content_type=ContentType.objects.get_for_model(StartupProfile),
        object_id=startup.uuid
    )

    r = auth_client.get(
        f"/api/users/{investor_user.id}/saved/?type=project"
    )

    assert r.data["count"] == 1
    assert r.data["results"][0]["type"] == "project"

def test_saved_list_unauthenticated(api_client, investor_user):
    r = api_client.get(f"/api/users/{investor_user.id}/saved/")
    assert r.status_code == 401
