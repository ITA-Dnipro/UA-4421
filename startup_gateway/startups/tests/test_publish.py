from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from startups.models import StartupProfile

User = get_user_model()

class StartupPublishTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.startup = StartupProfile.objects.create(
            user=self.user,
            company_name="Test Startup",
            slug="test-startup",
            short_pitch="A test startup",
            about_html="<p>About the test startup</p>",
            contact_email="test@example.com",
            contact_phone="1234567890",
            logo_url="http://example.com/logo.png",
            hero_image_url="http://example.com/hero.png",
        )

    def test_publish_startup_profile_success(self):
        response = self.client.post(f"/api/profiles/{self.startup.uuid}/publish/")
        self.assertEqual(response.status_code, 200)
        self.startup.refresh_from_db()
        self.assertTrue(self.startup.is_published)
        self.assertIsNotNone(self.startup.published_at)
        self.assertEqual(self.startup.published_by, self.user)

    def test_publish_startup_profile_missing_fields(self):
        self.startup.short_pitch = ""
        self.startup.save()

        response = self.client.post(f"/api/profiles/{self.startup.uuid}/publish/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing_fields", response.data)
        self.assertIn("short_pitch", response.data["missing_fields"])
        self.startup.refresh_from_db()
        self.assertFalse(self.startup.is_published)
        self.assertIsNone(self.startup.published_at)
        self.assertIsNone(self.startup.published_by)

    def test_publish_startup_profile_unauthorized(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(f"/api/profiles/{self.startup.uuid}/publish/")
        self.assertEqual(response.status_code, 401)
        self.startup.refresh_from_db()
        self.assertFalse(self.startup.is_published)
        self.assertIsNone(self.startup.published_at)
        self.assertIsNone(self.startup.published_by)

    def test_publish_startup_profile_not_found(self):
        response = self.client.post("/api/profiles/00000000-0000-0000-0000-000000000000/publish/")
        self.assertEqual(response.status_code, 404)
        self.startup.refresh_from_db()
        self.assertFalse(self.startup.is_published)
        self.assertIsNone(self.startup.published_at)
        self.assertIsNone(self.startup.published_by)