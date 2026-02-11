from datetime import datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import make_aware

from projects.models import Project, ProjectStatus
from startups.models import StartupProfile
from investors.models import InvestorProfile
from dashboard.models import SavedItem
from notifications.models import Notification
from notifications.tasks import handle_project_event, send_project_email
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="investor_email",
        email="investor_email@test.com",
        password="pass123",
    )


@pytest.fixture
def project(db):
    startup_user = User.objects.create_user(
        username="startup_email",
        email="startup_email@test.com",
        password="pass123",
    )
    startup_profile = StartupProfile.objects.create(
        user=startup_user,
        company_name="Test Startup",
    )

    return Project.objects.create(
        startup_profile=startup_profile,
        title="Email Project",
        slug="email-project",
        short_description="short",
        description="full",
        target_amount=1000,
        status=ProjectStatus.IDEA,
    )


@pytest.mark.django_db
def test_project_status_change_creates_notification():
    """
    When project status changes to 'active',
    a notification is created for investors who saved the startup.
    """

    startup_user = User.objects.create_user(
        username="startup",
        email="startup@test.com",
        password="pass123",
    )
    investor_user = User.objects.create_user(
        username="investor",
        email="investor@test.com",
        password="pass123",
    )

   
    startup_profile = StartupProfile.objects.create(
        user=startup_user,
        company_name="Test Startup",
    )

    investor_profile = InvestorProfile.objects.create(
        user=investor_user,
        company_name="Test Investor",
    )

    
    startup_ct = ContentType.objects.get_for_model(startup_profile)
    SavedItem.objects.create(
        investor_profile=investor_profile,
        content_type=startup_ct,
        object_id=startup_profile.uuid,
    )

    
    project = Project.objects.create(
        startup_profile=startup_profile,
        title="Test Project",
        slug="test-project",
        short_description="short",
        description="full",
        target_amount=1000,
        status=ProjectStatus.IDEA,
    )

    assert Notification.objects.count() == 0

    
    handle_project_event(
        event_type="project_status_changed",
        project_id=project.id,
        payload={
            "old_status": ProjectStatus.IDEA,
            "new_status": ProjectStatus.FUNDRAISING,
        },
    )

    
    notifications = Notification.objects.all()
    assert notifications.count() == 1

    notification = notifications.first()
    assert notification.user == investor_user
    assert notification.project == project
    assert notification.type == "project_status_changed"
    assert notification.payload["new_status"] == ProjectStatus.FUNDRAISING

    
    assert notification.event_key == f"project_status_changed:{project.id}:{investor_user.id}"
@pytest.mark.django_db
def test_project_event_idempotency():
    """
    Same project event should not create duplicate notifications
    due to event_key uniqueness.
    """

    user = User.objects.create_user(
        username="investor",
        email="investor@test.com",
        password="pass123",
    )

    startup_user = User.objects.create_user(
        username="startup",
        email="startup@test.com",
        password="pass123",
    )

    startup = StartupProfile.objects.create(
        user=startup_user,
        company_name="Test Startup",
    )

    investor = InvestorProfile.objects.create(
        user=user,
        company_name="Investor",
    )

    startup_ct = ContentType.objects.get_for_model(startup)
    SavedItem.objects.create(
        investor_profile=investor,
        content_type=startup_ct,
        object_id=startup.uuid,
    )

    project = Project.objects.create(
        startup_profile=startup,
        title="Test Project",
        slug="test-project",
        short_description="short",
        description="full",
        target_amount=1000,
        status=ProjectStatus.IDEA,
    )

    payload = {
        "old_status": ProjectStatus.IDEA,
        "new_status": ProjectStatus.FUNDRAISING,
    }

    # first call
    handle_project_event(
        event_type="project_status_changed",
        project_id=project.id,
        payload=payload,
    )

    # retry / duplicate call
    handle_project_event(
        event_type="project_status_changed",
        project_id=project.id,
        payload=payload,
    )

    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_notifications_api_list():
    user = User.objects.create_user(
        username="user",
        email="user@test.com",
        password="pass123",
    )

    Notification.objects.create(
        user=user,
        type="project_created",
        payload={"foo": "bar"},
        event_key=f"project_created:test:{user.id}",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/notifications/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["type"] == "project_created"

@pytest.mark.django_db
def test_notifications_mark_read():
    user = User.objects.create_user(
        username="user_mark_read",
        email="user@test.com",
        password="pass123",
    )

    notification = Notification.objects.create(
        user=user,
        type="project_created",
        payload={},
        is_read=False,
        event_key=f"project_created:mark_read:{user.id}",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.patch(f"/api/notifications/{notification.id}/read/")

    assert response.status_code in (200, 204)

    notification.refresh_from_db()
    assert notification.is_read is True

@pytest.mark.django_db
def test_status_change_triggers_notification_task():
    startup_user = User.objects.create_user(
        username="startup_2",
        email="startup2@test.com",
        password="pass123",
    )
    investor_user = User.objects.create_user(
        username="investor_2",
        email="investor2@test.com",
        password="pass123",
    )

    startup_profile = StartupProfile.objects.create(
        user=startup_user,
        company_name="Test Startup",
    )
    investor_profile = InvestorProfile.objects.create(
        user=investor_user,
        company_name="Test Investor",
    )

    startup_ct = ContentType.objects.get_for_model(startup_profile)
    SavedItem.objects.create(
        investor_profile=investor_profile,
        content_type=startup_ct,
        object_id=startup_profile.uuid,
    )

    project = Project.objects.create(
        startup_profile=startup_profile,
        title="Test Project",
        slug="test-project-status",
        short_description="short",
        description="full",
        target_amount=1000,
        status=ProjectStatus.IDEA,
    )

    client = APIClient()
    client.force_authenticate(user=startup_user)

    fixed_now = make_aware(datetime(2026, 2, 11, 12, 0, 0))

    with (
        patch("projects.views.now", return_value=fixed_now),
        patch("projects.views.handle_project_event.delay") as mock_task,
    ):
        response = client.patch(
            f"/api/projects/{project.id}/",
            data={"status": ProjectStatus.FUNDRAISING},
            format="json",
        )

        assert response.status_code == 200
        mock_task.assert_called_once()

        kwargs = mock_task.call_args.kwargs
        assert kwargs["event_type"] == "project_status_changed"
        assert kwargs["project_id"] == str(project.id)
        assert kwargs["payload"]["old_status"] == ProjectStatus.IDEA
        assert kwargs["payload"]["new_status"] == ProjectStatus.FUNDRAISING
        assert kwargs["payload"]["timestamp"] == fixed_now.isoformat()


def test_email_throttling(db, user, project):
    Notification.objects.create(
        user=user,
        project=project,
        type="project_status_changed",
        payload={"n": 1},
        event_key=f"project_status_changed:{project.id}:{user.id}:1",
    )

    result1 = send_project_email(user.id, project.id)
    assert "Email sent" in result1

    Notification.objects.create(
        user=user,
        project=project,
        type="project_status_changed",
        payload={"n": 2},
        event_key=f"project_status_changed:{project.id}:{user.id}:2",
    )

    result2 = send_project_email(user.id, project.id)
    assert "Email already sent" in result2


def test_email_batching(db, user, project):
    for i in range(3):
        Notification.objects.create(
            user=user,
            project=project,
            type="project_status_changed",
            payload={"n": i},
            event_key=f"project_status_changed:{project.id}:{user.id}:batch:{i}",
        )

    result = send_project_email(user.id, project.id)
    assert "(3 notifications)" in result

    assert (
        Notification.objects.filter(
            user=user,
            project=project,
            type="project_status_changed",
            is_read=False,
        ).count()
        == 0
    )


def test_email_idempotence(db, user, project):
    Notification.objects.create(
        user=user,
        project=project,
        type="project_status_changed",
        payload={"n": 1},
        event_key=f"project_status_changed:{project.id}:{user.id}:idem:1",
    )

    send_project_email(user.id, project.id)
    count_before = Notification.objects.filter(user=user, project=project).count()

    send_project_email(user.id, project.id)
    count_after = Notification.objects.filter(user=user, project=project).count()

    assert count_before == count_after
