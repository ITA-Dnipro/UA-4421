from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from startups.models import StartupProfile
from projects.models import Project, ProjectStatus, ProjectVisibility

User = get_user_model()


class ProjectPermissionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.owner_user = User.objects.create_user(username="owner", password="pass123")
        self.staff_user = User.objects.create_user(username="staff", password="pass123", is_staff=True)
        self.other_user = User.objects.create_user(username="other", password="pass123")

        self.startup = StartupProfile.objects.create(user=self.owner_user)
        self.startup_projects_url = reverse("projects:startup-projects", kwargs={"startup_id": self.startup.id})

        self.project = Project.objects.create(
            startup_profile=self.startup,
            title="Test Project",
            slug="test-project",
            short_description="desc",
            description="desc",
            status=ProjectStatus.FUNDRAISING,
            target_amount=100,
            raised_amount=0,
            currency="UAH",
            visibility=ProjectVisibility.PRIVATE
        )

    def auth_as(self, user):
        token = str(AccessToken.for_user(user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def clear_auth(self):
        self.client.credentials()

    def project_payload(self, slug="handmade-chairs"):
        return {
            "title": "Handmade Chairs",
            "slug": slug,
            "short_description": "short",
            "description": "long description",
            "status": "idea",
            "target_amount": "50000.00",
            "raised_amount": "0.00",
            "currency": "UAH",
            "visibility": "public",
        }

    def test_staff_can_create_project_for_any_startup(self):
        self.auth_as(self.staff_user)
        resp = self.client.post(self.startup_projects_url, data=self.project_payload(slug="staff-project"), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Project.objects.filter(slug="staff-project").exists())

    def test_non_owner_cannot_create_project(self):
        self.auth_as(self.other_user)
        resp = self.client.post(self.startup_projects_url, data=self.project_payload(slug="blocked-project"), format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Project.objects.filter(slug="blocked-project").exists())

    def test_staff_can_modify_any_project(self):
        self.auth_as(self.staff_user)
        url = reverse("projects:project-rud", kwargs={"pk": self.project.pk})
        resp = self.client.patch(url, data={"short_description": "staff updated"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.short_description, "staff updated")

    def test_owner_can_modify_own_project(self):
        self.auth_as(self.owner_user)
        url = reverse("projects:project-rud", kwargs={"pk": self.project.pk})
        resp = self.client.patch(url, data={"short_description": "owner updated"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.short_description, "owner updated")

    def test_non_owner_cannot_modify_project(self):
        self.project.visibility = ProjectVisibility.PUBLIC
        self.project.save()
        self.auth_as(self.other_user)
        url = reverse("projects:project-rud", kwargs={"pk": self.project.pk})
        resp = self.client.patch(url, data={"short_description": "hacked"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.project.refresh_from_db()
        self.assertEqual(self.project.short_description, "desc")
