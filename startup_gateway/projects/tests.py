from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from django.contrib.auth import get_user_model

from startups.models import StartupProfile
from projects.models import Project, ProjectStatus


class ProjectsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()

        self.owner_user = User.objects.create_user(username="owner", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")

        self.startup = StartupProfile.objects.create(user=self.owner_user)

        self.startup_projects_url = reverse("projects:startup-projects", kwargs={"startup_id": self.startup.id})

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

    def test_create_success_owner(self):
        self.auth_as(self.owner_user)

        resp = self.client.post(self.startup_projects_url, data=self.project_payload(slug="handmade-chairs-a"), format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", resp.data)
        self.assertEqual(resp.data["title"], "Handmade Chairs")

        self.assertIn("Location", resp.headers)

        project_id = resp.data["id"]
        self.assertTrue(Project.objects.filter(pk=project_id, startup_profile=self.startup).exists())

    def test_create_unauthorized_no_token(self):
        self.clear_auth()

        resp = self.client.post(self.startup_projects_url, data=self.project_payload(slug="handmade-chairs-b"), format="json")

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_forbidden_non_owner(self):
        self.auth_as(self.other_user)

        resp = self.client.post(self.startup_projects_url, data=self.project_payload(slug="handmade-chairs-c"), format="json")

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Project.objects.filter(startup_profile=self.startup).count(), 0)

    def test_owner_update_works(self):
        project = Project.objects.create(
            startup_profile=self.startup,
            title="Old title",
            slug="old-slug",
            short_description="old",
            description="old desc",
            status="idea",
            target_amount="100.00",
            raised_amount="0.00",
            currency="UAH",
            visibility="public",
        )

        self.auth_as(self.owner_user)

        url = reverse("projects:project-rud", kwargs={"pk": project.pk})
        resp = self.client.patch(url, data={"short_description": "updated"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        project.refresh_from_db()
        self.assertEqual(project.short_description, "updated")

    def test_non_owner_update_forbidden(self):
        project = Project.objects.create(
            startup_profile=self.startup,
            title="Title",
            slug="slug-1",
            short_description="orig",
            description="desc",
            status="idea",
            target_amount="100.00",
            raised_amount="0.00",
            currency="UAH",
            visibility="public",
        )

        self.auth_as(self.other_user)

        url = reverse("projects:project-rud", kwargs={"pk": project.pk})
        resp = self.client.patch(url, data={"short_description": "hacked"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        project.refresh_from_db()
        self.assertEqual(project.short_description, "orig")




class ProjectCustomActionsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()

        self.owner_user = User.objects.create_user(username="owner", password="pass12345")
        self.admin_user = User.objects.create_user(username="admin", password="pass12345", is_staff=True)
        self.other_user = User.objects.create_user(username="other", password="pass12345")

        self.startup = StartupProfile.objects.create(user=self.owner_user)

        self.project = Project.objects.create(
            startup_profile=self.startup,
            title="Test Project",
            slug="test-project",
            short_description="desc",
            description="desc",
            status=ProjectStatus.FUNDRAISING,
            target_amount="100.00",
            raised_amount="0.00",
            currency="UAH",
            visibility="public",
            allow_overfunding=False
        )

    def auth_as(self, user):
        token = str(AccessToken.for_user(user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def clear_auth(self):
        self.client.credentials()

    def _status_url(self):
        return reverse("projects:project-status-update", kwargs={"pk": self.project.pk})

    def _raised_amount_url(self):
        return reverse("projects:update-raised-amount", kwargs={"pk": self.project.pk})

    # ----------------- Status update tests -----------------
    def test_status_update_success(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"status": ProjectStatus.FUNDED}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)

    def test_status_update_invalid_transition(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"status": ProjectStatus.IDEA}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid status transition", resp.data["detail"])
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDRAISING)

    def test_status_update_admin_override(self):
        self.auth_as(self.admin_user)
        resp = self.client.patch(self._status_url(), data={"status": ProjectStatus.MVP}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.MVP)

    # ----------------- Raised amount tests -----------------
    def test_update_raised_amount_success(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._raised_amount_url(), data={"raised_amount": "50.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 50.0)
        self.assertEqual(self.project.status, ProjectStatus.FUNDRAISING) 

    def test_update_raised_amount_to_target(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._raised_amount_url(), data={"raised_amount": "100.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 100.0)
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertIsNotNone(self.project.funded_at)

    def test_update_raised_amount_over_target_not_allowed(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._raised_amount_url(), data={"raised_amount": "150.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Raised amount cannot exceed target amount", resp.data["detail"])
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 0.0) 