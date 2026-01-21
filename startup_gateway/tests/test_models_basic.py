import pytest
from django.contrib.auth import get_user_model
from startups.models import StartupProfile
from users.models import User, Role, UserRole


User = get_user_model()


@pytest.mark.django_db
def test_create_user_basic():
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password123",
    )

    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.check_password("password123") is True


@pytest.mark.django_db
def test_role_creation():
    role = Role.objects.create(name="startup")

    assert role.name == "startup"
    assert str(role) == "startup"

@pytest.mark.django_db
def test_user_with_role():
    user = User.objects.create_user(
        username="roleuser",
        password="password123",
    )
    role = Role.objects.create(name="investor")

    UserRole.objects.create(user=user, role=role)

    assert role in user.roles.all()
    assert user in role.users.all()

@pytest.mark.django_db
def test_startup_profile_creation():
    user = User.objects.create(
        email="founder@example.com",
        password="password123"
    )

    profile = StartupProfile.objects.create(
        user=user,
        company_name="Test Startup",
        short_pitch="We build cool stuff",
        website="https://example.com",
    )

    assert profile.user == user
    assert profile.company_name == "Test Startup"
    assert str(profile) == "Test Startup"