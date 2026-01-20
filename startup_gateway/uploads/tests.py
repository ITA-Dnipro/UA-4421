from django.test import TestCase, APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from uploads.models import Upload
from projects.models import Project, ProjectAttachment

class UploadModelTest(TestCase):

    def test_create_image_upload(self):
        file = SimpleUploadedFile(
            name="test.jpg",
            content=b"\xff\xd8\xff\xe0",
            content_type="image/jpeg"
        )

        upload = Upload.objects.create(
            file=file,
            mime_type="image/jpeg",
            size=file.size
        )

        self.assertIsNotNone(upload.id)
        self.assertEqual(upload.mime_type, "image/jpeg")


def create_upload(name, content, content_type):
    file = SimpleUploadedFile(
        name=name,
        content=content,
        content_type=content_type
    )
    return Upload.objects.create(
        file=file,
        mime_type=content_type,
        size=file.size
    )


class ProjectAttachmentTests(APITestCase):

    def test_attach_image_success(self):
        upload = create_upload(
            "img.jpg",
            b"\xff\xd8\xff\xe0",
            "image/jpeg"
        )

        response = self.client.post(
            "/api/projects/",
            {
                "title": "Test project",
                "description": "Desc",
                "attachments": [
                    {
                        "upload_id": upload.id,
                        "role": "thumbnail"
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(ProjectAttachment.objects.count(), 1)


    def test_invalid_file_type_rejected(self):
        upload = create_upload(
            "file.pdf",
            b"%PDF-1.4",
            "application/pdf"
        )

        response = self.client.post(
            "/api/projects/",
            {
                "title": "Test project",
                "description": "Desc",
                "attachments": [
                    {
                        "upload_id": upload.id,
                        "role": "thumbnail"
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Thumbnail", str(response.data))


    def test_large_file_rejected(self):
        upload = create_upload(
            "big.jpg",
            b"x" * (6 * 1024 * 1024),  # 6MB
            "image/jpeg"
        )

        response = self.client.post(
            "/api/projects/",
            {
                "title": "Test project",
                "description": "Desc",
                "attachments": [
                    {
                        "upload_id": upload.id,
                        "role": "thumbnail"
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("large", str(response.data).lower())