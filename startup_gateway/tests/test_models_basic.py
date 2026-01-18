import pytest
from django.contrib.auth import get_user_model
from startup_gateway.startups.models import StartupProfile


User = get_user_model()


@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(
        email="test@example.com",
        password="password123"
    )

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.check_password("password123")


@pytest.mark.django_db
def test_startup_profile_creation():
    user = User.objects.create_user(
        email="founder@example.com",
        password="password123"
    )

    profile = StartupProfile.objects.create(
        user=user,
        company_name="Test Startup"  
    )

    assert profile.id is not None
    assert profile.user == user
    assert profile.company_name == "Test Startup"