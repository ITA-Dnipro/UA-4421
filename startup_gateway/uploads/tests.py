from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from startups.models import StartupProfile

User = get_user_model()


class UploadCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/uploads/"

    def test_attach_image_success(self):
        image = SimpleUploadedFile(
            name="test.jpg",
            content=b"\xff\xd8\xff\xe0" + b"0" * 1024,
            content_type="image/jpeg"
        )

        response = self.client.post(
            self.url,
            {"file": image, "purpose": "logo"},
            format="multipart"
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["type"], "image")

    def test_missing_file_rejected_field_level(self):
        response = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)
        self.assertIn("required", str(response.data["file"]).lower())

    def test_invalid_file_type_rejected(self):
        file = SimpleUploadedFile(
            name="virus.exe",
            content=b"malicious content",
            content_type="application/octet-stream"
        )

        response = self.client.post(
            self.url,
            {"file": file},
            format="multipart"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)
        self.assertIn("Invalid file type", str(response.data["file"]))

    def test_large_file_rejected(self):
        big_file = SimpleUploadedFile(
            name="big.pdf",
            content=b"0" * (11 * 1024 * 1024),
            content_type="application/pdf"
        )

        response = self.client.post(
            self.url,
            {"file": big_file, "purpose": "pitch_deck"},
            format="multipart"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)
        self.assertIn("Document too large", str(response.data["file"]))


class UploadProjectFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)

        self.startup = StartupProfile.objects.create(
            company_name="Test startup",
            slug="test-startup",
            user=self.user
        )

    def test_upload_then_attach_to_project(self):
        image = SimpleUploadedFile(
            name="a.jpg",
            content=b"\xff\xd8\xff" + b"0" * 1024,
            content_type="image/jpeg"
        )

        upload_resp = self.client.post(
            "/api/uploads/",
            {"file": image, "purpose": "logo"},
            format="multipart"
        )
        self.assertEqual(upload_resp.status_code, 201)

        upload_id = upload_resp.data["id"]

        project_resp = self.client.post(
            f"/api/startups/{self.startup.id}/projects/",
            {
                "title": "Test project",
                "slug": "test-project",
                "short_description": "Short desc",
                "description": "Long desc",
                "target_amount": 1
            },
            format="json"
        )

        self.assertEqual(project_resp.status_code, 201)
        project_id = project_resp.data["id"]

        attach_resp = self.client.post(
            "/api/projects/attachments/create/",
            {
                "project": project_id,
                "upload": upload_id,
                "type": "thumbnail"
            },
            format="json"
        )

        self.assertEqual(attach_resp.status_code, 201)
        self.assertEqual(str(attach_resp.data["project"]), project_id)
        self.assertEqual(attach_resp.data["upload"], upload_id)

        project_detail_resp = self.client.get(f"/api/projects/{project_id}/")
        self.assertEqual(project_detail_resp.status_code, 200)
        self.assertIn("upload_url", project_detail_resp.data["attachments"][0])
