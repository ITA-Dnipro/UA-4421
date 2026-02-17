from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from projects.models import Project, ProjectAudit
from startups.models import StartupProfile
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectAuditTests(APITestCase):

    def setUp(self):

        self.user = User.objects.create_user(username="user1", password="pass123")
        self.staff_user = User.objects.create_user(username="staff", password="pass123", is_staff=True)
        self.startup = StartupProfile.objects.create(user=self.user, name="Test Startup")

        self.project_data = {
            "title": "My Project",
            "slug": "my-project",
            "short_description": "Short desc",
            "description": "Long description",
            "target_amount": 1000,
            "currency": "USD",
            "status": "idea",
            "visibility": "public",
            "allow_overfunding": False
        }

        self.client.force_authenticate(user=self.user)

    def test_create_project_creates_audit(self):
        url = reverse("projects:startup-projects-list-create", kwargs={"startup_id": self.startup.id})
        response = self.client.post(url, self.project_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        project = Project.objects.get(pk=response.data["id"])
        audit = ProjectAudit.objects.filter(project=project, action="create").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, self.user)
        self.assertIn("title", audit.changes)

    def test_update_project_creates_audit(self):
        project = Project.objects.create(startup_profile=self.startup, **self.project_data)

        url = reverse("projects:project-rud", kwargs={"pk": project.id})
        update_data = {"title": "Updated Project"}
        response = self.client.patch(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        audit = ProjectAudit.objects.filter(project=project, action="update").last()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes["title"]["before"], project.title)
        self.assertEqual(audit.user, self.user)

    def test_delete_project_creates_audit(self):
        project = Project.objects.create(startup_profile=self.startup, **self.project_data)

        url = reverse("projects:project-rud", kwargs={"pk": project.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        project.refresh_from_db()
        self.assertTrue(project.is_deleted)
        audit = ProjectAudit.objects.filter(project=project, action="delete").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes["is_deleted"]["after"], True)

    def test_project_history_endpoint(self):
        project = Project.objects.create(startup_profile=self.startup, **self.project_data)
        project.title = "Title v2"
        project.save()
        ProjectAudit.objects.create(project=project, user=self.user, action="update", changes={"title": {"before": "My Project", "after": "Title v2"}})

        url = reverse("projects:project-history", kwargs={"pk": project.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data["results"]) >= 1)
        self.assertIn("action", response.data["results"][0])

    def test_project_revert_restores_previous_state(self):
        project = Project.objects.create(startup_profile=self.startup, **self.project_data)

        project.title = "Title v2"
        project.save()
        audit = ProjectAudit.objects.create(project=project, user=self.user, action="update",
                                            changes={"title": {"before": "My Project", "after": "Title v2"}})

        url = reverse("projects:project-revert", kwargs={"pk": project.id, "audit_id": audit.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project.refresh_from_db()
        self.assertEqual(project.title, "My Project")

        revert_audit = ProjectAudit.objects.filter(project=project, action="revert").last()
        self.assertIsNotNone(revert_audit)
        self.assertEqual(revert_audit.user, self.user)
