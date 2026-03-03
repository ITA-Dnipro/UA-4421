import shutil
import tempfile
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from startups.models import StartupProfile
from uploads.models import Upload

User = get_user_model()


class StartupProfileMeUploadsTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp(prefix="test-media-")
        self._override = override_settings(MEDIA_ROOT=self._media_root)
        self._override.enable()

        self.client = APIClient()

        self.user = User.objects.create_user(
            username="startup_user",
            email="startup_user@test.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)

        self.profile = StartupProfile.objects.create(
            user=self.user,
            company_name="Test Startup",
            slug="test-startup",
        )

        self.url = "/api/startups/me/"

    def tearDown(self):
        self._override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _create_upload(self, *, name: str, content: bytes, content_type: str, upload_type: str, user=None) -> Upload:
        f = SimpleUploadedFile(name=name, content=content, content_type=content_type)
        return Upload.objects.create(
            user=user or self.user,
            file=f,
            type=upload_type,
            size=f.size,
            content_type=content_type,
        )

    def test_patch_logo_upload_id_sets_logo_url(self):
        upload = self._create_upload(
            name="logo.jpg",
            content=b"\xff\xd8\xff" + b"0" * 50,
            content_type="image/jpeg",
            upload_type="image",
        )

        resp = self.client.patch(self.url, {"logo_upload_id": upload.id}, format="json")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        expected = f"http://testserver{upload.file.url}"

        self.assertEqual(self.profile.logo_url, expected)
        self.assertEqual(resp.data["logo_url"], expected)

    def test_patch_logo_upload_id_not_found(self):
        resp = self.client.patch(self.url, {"logo_upload_id": 999999}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("logo_upload_id", resp.data)
        self.assertIn("Upload not found", str(resp.data["logo_upload_id"]))

    def test_patch_logo_upload_id_wrong_type(self):
        upload = self._create_upload(
            name="deck.pdf",
            content=b"%PDF-1.4\n" + b"0" * 50,
            content_type="application/pdf",
            upload_type="doc",
        )

        resp = self.client.patch(self.url, {"logo_upload_id": upload.id}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("logo_upload_id", resp.data)
        self.assertIn("not an image", str(resp.data["logo_upload_id"]).lower())

    def test_patch_pitch_deck_upload_id_sets_pitch_deck_url(self):
        upload = self._create_upload(
            name="deck.pdf",
            content=b"%PDF-1.4\n" + b"0" * 50,
            content_type="application/pdf",
            upload_type="doc",
        )

        resp = self.client.patch(self.url, {"pitch_deck_upload_id": upload.id}, format="json")
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        expected = f"http://testserver{upload.file.url}"

        self.assertEqual(self.profile.pitch_deck_url, expected)
        self.assertEqual(resp.data["pitch_deck_url"], expected)

    def test_patch_pitch_deck_upload_id_not_found(self):
        resp = self.client.patch(self.url, {"pitch_deck_upload_id": 999999}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pitch_deck_upload_id", resp.data)
        self.assertIn("Upload not found", str(resp.data["pitch_deck_upload_id"]))

    def test_patch_pitch_deck_upload_id_wrong_type(self):
        upload = self._create_upload(
            name="logo.png",
            content=b"\x89PNG\r\n\x1a\n" + b"0" * 50,
            content_type="image/png",
            upload_type="image",
        )

        resp = self.client.patch(self.url, {"pitch_deck_upload_id": upload.id}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pitch_deck_upload_id", resp.data)
        self.assertIn("not a document", str(resp.data["pitch_deck_upload_id"]).lower())
    
    def test_patch_logo_upload_id_other_user_upload_rejected(self):
        token = uuid.uuid4().hex
        other_user = User.objects.create_user(
            username=f"other_{token}",
            email=f"other_{token}@test.com",
            password="pass12345",
        )

        foreign_upload = self._create_upload(
            name="logo.jpg",
            content=b"\xff\xd8\xff" + b"0" * 50,
            content_type="image/jpeg",
            upload_type="image",
            user=other_user,
        )

        response = self.client.patch(self.url, {"logo_upload_id": foreign_upload.id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("logo_upload_id", response.data)
        self.assertIn("Upload not found", str(response.data["logo_upload_id"]))
       
        
    def test_patch_pitch_deck_upload_id_other_user_upload_rejected(self):
        token = uuid.uuid4().hex
        other_user = User.objects.create_user(
            username=f"other_{token}",
            email=f"other_{token}@test.com",
            password="pass12345",
        )

        foreign_upload = self._create_upload(
            name="pitch_deck.pdf",
            content=b"%PDF-1.4\n%fake\n" + b"0" * 50,
            content_type="application/pdf",
            upload_type="doc",
            user=other_user,
        )

        response = self.client.patch(
            self.url,
            {"pitch_deck_upload_id": foreign_upload.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("pitch_deck_upload_id", response.data)
        self.assertIn("Upload not found", str(response.data["pitch_deck_upload_id"]))



