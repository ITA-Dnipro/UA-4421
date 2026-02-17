from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from django.contrib.auth import get_user_model

from startups.models import StartupProfile
from unittest.mock import patch
from projects.models import Project, ProjectStatus, ProjectVisibility, ModerationStatus, ModerationAction

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



@patch('search.backends.meilisearch.MeiliSearchBackend.__init__', return_value=None)
@patch('search.services.ProjectSearchService.index_project', return_value=None)
@patch('search.services.ProjectSearchService.remove_project', return_value=None)
class ProjectCustomActionsAPITests(TransactionTestCase):

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
            visibility=ProjectVisibility.PRIVATE,
            allow_overfunding=False
        )

    def auth_as(self, user):
        token = str(AccessToken.for_user(user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def clear_auth(self):
        self.client.credentials()

    def _status_url(self):
        return reverse("projects:project-state-service", kwargs={"pk": self.project.pk})

    def test_status_update_success(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        self.project.raised_amount = 100
        self.project.save(update_fields=["raised_amount"])

        resp = self.client.patch(self._status_url(), data={"status": ProjectStatus.FUNDED}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertIsNotNone(self.project.funded_at)

    def test_status_update_invalid_transition(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"status": ProjectStatus.FUNDED}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Target amount not reached yet.", resp.data["detail"])
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDRAISING)


    def test_set_raised_amount_success(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"raised_amount": "50.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 50.0)
        self.assertEqual(self.project.status, ProjectStatus.FUNDRAISING)

    def test_set_raised_amount_to_target(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"raised_amount": "100.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 100.0)
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertIsNotNone(self.project.funded_at)

    def test_set_raised_amount_over_target_not_allowed(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"raised_amount": "150.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Overfunding is not allowed.", resp.data["detail"])
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.raised_amount), 0.0)

    def test_change_visibility_to_public(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        resp = self.client.patch(self._status_url(), data={"visibility": ProjectVisibility.PUBLIC}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.visibility, ProjectVisibility.PUBLIC)

    def test_partial_update_status_and_amount(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        resp = self.client.patch(
            self._status_url(),
            data={"raised_amount": "100.00", "status": ProjectStatus.FUNDED, "visibility": ProjectVisibility.PUBLIC},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)
        self.assertEqual(float(self.project.raised_amount), 100.0)
        self.assertIsNotNone(self.project.funded_at)
        self.assertEqual(self.project.visibility, ProjectVisibility.PUBLIC)

    def test_change_visibility_to_public_triggers_indexing(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)
        
        resp = self.client.patch(
            self._status_url(), 
            data={"visibility": ProjectVisibility.PUBLIC}, 
            format="json"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        mock_index.assert_called_once()
        called_project = mock_index.call_args[0][0]
        self.assertEqual(called_project.pk, self.project.pk)


    def test_change_visibility_to_private_triggers_removal(self, mock_remove, mock_index, *args):
        self.project.visibility = ProjectVisibility.PUBLIC
        self.project.save()
        
        self.auth_as(self.owner_user)

        resp = self.client.patch(
            self._status_url(), 
            data={"visibility": ProjectVisibility.PRIVATE}, 
            format="json"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_remove.assert_called_once()

    def test_indexing_happens_only_after_commit(self, mock_remove, mock_index, *args):
        self.auth_as(self.owner_user)

        resp = self.client.patch(
            self._status_url(), 
            data={"status": "invalid_status"}, 
            format="json"
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_index.assert_not_called()

class AdminModerationAPITest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.startup_user = User.objects.create_user(
            username="startup", email="startup@test.com", password="pass123"
        )

        self.startup = StartupProfile.objects.create(
            user=self.startup_user, company_name="Tech Inc"
        )

        self.project = Project.objects.create(
            startup_profile=self.startup,
            title="Test Project",
            slug="test-project",
            short_description="desc",
            description="desc",
            moderation_status=ModerationStatus.PENDING,
            target_amount=10000.00
        )

        self.client = APIClient()

    def test_non_admin_forbidden_list(self):
        self.client.force_authenticate(user=self.startup_user)
        response = self.client.get(reverse('projects:admin-project-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_list_projects(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('projects:admin-project-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_approve_project(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            reverse('projects:admin-project-moderate', kwargs={'id': self.project.id}),
            {'action': ModerationAction.APPROVE},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.moderation_status, ModerationStatus.APPROVED)

    def test_reject_project(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            reverse('projects:admin-project-moderate', kwargs={'id': self.project.id}),
            {'action': ModerationAction.REJECT, 'reason': 'Violates guidelines'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.moderation_status, ModerationStatus.REJECTED)

    def test_flag_project(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            reverse('projects:admin-project-moderate', kwargs={'id': self.project.id}),
            {'action': ModerationAction.FLAG, 'reason': 'Suspicious content'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.moderation_status, ModerationStatus.FLAGGED)

    def test_reject_without_reason_fails(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            reverse('projects:admin-project-moderate', kwargs={'id': self.project.id}),
            {'action': ModerationAction.REJECT},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

