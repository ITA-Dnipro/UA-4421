from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.signing import SignatureExpired
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APITestCase

from startups.models import StartupProfile
from investors.models import InvestorProfile


User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestRegisterApi(APITestCase):
    def test_happy_path_startup(self):
        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
            "short_pitch": "Woodwork & ceramics",
            "website": "https://example.com",
            "contact_phone": "+380123456789",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertIn("detail", resp.data)

        user = User.objects.get(email="alice@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.verified)
        self.assertTrue(user.roles.filter(name="startup").exists())
        self.assertTrue(
            StartupProfile.objects.filter(
                user=user,
                company_name="Handmade Co",
                short_pitch="Woodwork & ceramics",
                website="https://example.com",
            ).exists()
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify-email/?token=", mail.outbox[0].body)

    def test_happy_path_investor(self):
        payload = {
            "email": "investor@example.com",
            "password": "P@ssw0rd!123",
            "role": "investor",
            "company_name": "Example Investor",
            "contact_phone": "+380123456780",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertIn("detail", resp.data)

        user = User.objects.get(email="investor@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.verified)
        self.assertTrue(user.roles.filter(name="investor").exists())
        self.assertTrue(
            InvestorProfile.objects.filter(
                user=user,
                company_name="Example Investor",
            ).exists()
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify-email/?token=", mail.outbox[0].body)

    def test_validation_missing_company_name(self):
        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
        }

        resp = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("company_name", resp.data)

    def test_validation_password_rules(self):
        payload = {
            "email": "alice@example.com",
            "password": "123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        resp = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.data)

    def test_validation_investor_disallow_startup_fields(self):
        payload = {
            "email": "investor2@example.com",
            "password": "P@ssw0rd!123",
            "role": "investor",
            "company_name": "Example Investor",
            "website": "https://example.com",
        }

        resp = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("website", resp.data)

    def test_duplicate_verified_email_no_side_effects(self):
        User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="P@ssw0rd!123",
            verified=True,
            is_active=True,
        )

        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(User.objects.filter(email="alice@example.com").count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_unverified_resends_email(self):
        User.objects.create_user(
            username="alice@example.com",
            email="alice@example.com",
            password="P@ssw0rd!123",
            verified=False,
            is_active=False,
        )

        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(User.objects.filter(email="alice@example.com").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify-email/?token=", mail.outbox[0].body)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestVerifyEmailApi(APITestCase):
    def test_verify_email_happy_path(self):
        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        body = mail.outbox[0].body
        token = body.split("token=", 1)[1].strip()

        verify_resp = self.client.get(f"/api/auth/verify-email/?token={token}")
        self.assertEqual(verify_resp.status_code, 200)

        user = User.objects.get(email="alice@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.verified)

    def test_verify_email_invalid_token(self):
        resp = self.client.get("/api/auth/verify-email/?token=bad")
        self.assertEqual(resp.status_code, 400)
        
    def test_verify_email_post_happy_path(self):
        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        body = mail.outbox[0].body
        token = body.split("token=", 1)[1].strip()

        verify_resp = self.client.post("/api/auth/verify-email/", {"token": token}, format="json")
        self.assertEqual(verify_resp.status_code, 200)

        user = User.objects.get(email="alice@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.verified)


    def test_verify_email_post_single_use(self):
        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        body = mail.outbox[0].body
        token = body.split("token=", 1)[1].strip()

        first = self.client.post("/api/auth/verify-email/", {"token": token}, format="json")
        self.assertEqual(first.status_code, 200)

        second = self.client.post("/api/auth/verify-email/", {"token": token}, format="json")
        self.assertEqual(second.status_code, 400)

        user = User.objects.get(email="alice@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.verified)


    def test_verify_email_post_expired_token(self):
        with patch("users.services.TimestampSigner.unsign", side_effect=SignatureExpired("expired")):
            resp = self.client.post("/api/auth/verify-email/", {"token": "any"}, format="json")
        self.assertEqual(resp.status_code, 400)

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_VERIFICATION_RESEND_EMAIL_TTL=60,
    EMAIL_VERIFICATION_RESEND_IP_TTL=60,
)
class TestResendVerificationApi(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_resend_returns_200_for_non_existing_email(self):
        resp = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "missing@example.com"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_throttles_multiple_calls(self):
        user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="P@ssw0rd!123",
            verified=False,
            is_active=False,
        )

        first = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "alice@example.com"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        user.refresh_from_db()
        nonce_after_first = user.email_verification_nonce

        second = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "alice@example.com"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        user.refresh_from_db()
        self.assertEqual(user.email_verification_nonce, nonce_after_first)
