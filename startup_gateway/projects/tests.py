from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from django.contrib.auth import get_user_model

from startups.models import StartupProfile
from projects.models import Project, ProjectStatus, ProjectVisibility, ModerationStatus, ModerationAction
from django.test import TestCase
from projects.services.moderation_service import ProjectModerationService

User = get_user_model()


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
        return reverse("projects:project-state-service", kwargs={"pk": self.project.pk})

    # ----------------- Status update tests -----------------
    def test_status_update_success(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"status": ProjectStatus.FUNDED}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertIsNotNone(self.project.funded_at)

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
        resp = self.client.patch(self._status_url(), data={"raised_amount": "50.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 50.0)
        self.assertEqual(self.project.status, ProjectStatus.FUNDRAISING)

    def test_update_raised_amount_to_target(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"raised_amount": "100.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 100.0)
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertIsNotNone(self.project.funded_at)

    def test_update_raised_amount_over_target_not_allowed(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"raised_amount": "150.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Raised amount cannot exceed target amount", resp.data["detail"])
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 0.0)

    # ----------------- Combined update test -----------------
    def test_partial_update_status_and_amount(self):
        self.auth_as(self.owner_user)
        resp = self.client.patch(
            self._status_url(),
            data={"status": ProjectStatus.FUNDED, "raised_amount": "100.00"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertEqual(float(self.project.raised_amount), 100.0)
        self.assertIsNotNone(self.project.funded_at)


class AdminProjectAPITest(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@test.com", password="admin123", is_staff=True
        )
        self.startup_user = User.objects.create_user(
            username="startup", email="startup@test.com", password="pass123"
        )

        self.startup = StartupProfile.objects.create(
            user=self.startup_user, company_name="Tech Inc", slug="tech-inc"
        )

        self.project1 = Project.objects.create(
            startup_profile=self.startup,
            title="Project 1",
            slug="project-1",
            short_description="Short description 1",
            description="Description of project 1",
            moderation_status=ModerationStatus.PENDING,
            target_amount=10000.00,
            raised_amount=0.00,
            currency="UAH",
        )

        self.project2 = Project.objects.create(
            startup_profile=self.startup,
            title="Project 2",
            slug="project-2",
            short_description="Short description 2",
            description="Description of project 2",
            moderation_status=ModerationStatus.APPROVED,
            target_amount=20000.00,
            raised_amount=5000.00,
            currency="UAH",
        )

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(user=self.startup_user)
        response = self.client.get(reverse('projects:admin-project-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_projects(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('projects:admin-project-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreater(len(response.data['results']), 0)


class ProjectModerationServiceTest(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@test.com", password="admin123", is_staff=True
        )
        self.startup_user = User.objects.create_user(
            username="startup", email="startup@test.com", password="pass123"
        )

        self.startup = StartupProfile.objects.create(
            user=self.startup_user, company_name="Tech Inc", slug="tech-inc"
        )

        self.project = Project.objects.create(
            startup_profile=self.startup,
            title="Sample Project",
            slug="sample-project",
            short_description="A short description",
            description="A detailed description",
            moderation_status=ModerationStatus.PENDING,
            target_amount=10000.00,
            raised_amount=0.00,
            currency="UAH",
            status=ProjectStatus.IDEA,
        )

    def test_approve_project(self):
        success, message, project = ProjectModerationService.moderate_project(
            self.project, ModerationAction.APPROVE, self.admin_user
        )

        self.assertTrue(success)
        self.assertEqual(message, 'Project approved successfully')
        self.assertEqual(project.moderation_status, ModerationStatus.APPROVED)

    def test_reject_requires_reason(self):
        success, message, _ = ProjectModerationService.moderate_project(
            self.project, ModerationAction.REJECT, self.admin_user
        )
        self.assertFalse(success)
        self.assertIn("reason is required", message.lower())

    def test_reject_project(self):
        reason = "Violates guidelines"
        success, message, project = ProjectModerationService.moderate_project(
            self.project, ModerationAction.REJECT, self.admin_user, reason
        )
        self.assertTrue(success)
        self.assertEqual(message, "Project rejected and owner notified")
        self.assertEqual(project.moderation_status, ModerationStatus.REJECTED)
        self.assertEqual(project.rejection_reason, reason)

    def test_cannot_approve_deleted_project(self):
        self.project.is_deleted = True
        self.project.save()

        success, message, _ = ProjectModerationService.moderate_project(
            self.project, ModerationAction.APPROVE, self.admin_user
        )
        self.assertFalse(success)
        self.assertIn("cannot approve deleted project", message.lower())

    def test_soft_delete_project(self):
        success, message, project = ProjectModerationService.moderate_project(
            self.project, ModerationAction.DELETE, self.admin_user, reason="Spam"
        )

        self.assertTrue(success)
        self.assertEqual(message, "Project deleted successfully")
        self.assertTrue(project.is_deleted)

    def test_restore_project(self):
        self.project.is_deleted = True
        self.project.save()

        success, message, project = ProjectModerationService.moderate_project(
            self.project, ModerationAction.RESTORE, self.admin_user
        )

        self.assertTrue(success)
        self.assertEqual(message, "Project restored successfully")
        self.assertFalse(project.is_deleted)
