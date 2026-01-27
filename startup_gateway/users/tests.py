from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.core.cache import cache
from rest_framework.test import APITestCase
from importlib import reload

from startups.models import StartupProfile
from investors.models import InvestorProfile
from users.models import PasswordResetAttempt, Role
from users.tokens import password_reset_token_generator
from users import tokens

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


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetApi(APITestCase):

    def setUp(self):
        cache.clear()
        mail.outbox = []

        self.startup_role, _ = Role.objects.get_or_create(name='startup')

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=True,
            verified=True,
        )
        self.user.roles.add(self.startup_role)

    def tearDown(self):
        cache.clear()

    def test_happy_path_known_email(self):
        payload = {"email": "test@example.com"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("detail", resp.data)
        self.assertEqual(
            resp.data["detail"],
            "If the email exists, you will receive reset instructions."
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertIn('Password Reset', mail.outbox[0].subject)
        self.assertIn('reset-password', mail.outbox[0].body)

        attempt = PasswordResetAttempt.objects.get(email='test@example.com')
        self.assertEqual(attempt.user, self.user)
        self.assertTrue(attempt.token_sent)

    def test_unknown_email_returns_200_no_email(self):
        payload = {"email": "unknown@example.com"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("detail", resp.data)

        self.assertEqual(len(mail.outbox), 0)

        attempt = PasswordResetAttempt.objects.get(email='unknown@example.com')
        self.assertIsNone(attempt.user)
        self.assertFalse(attempt.token_sent)

    def test_inactive_user_no_email(self):
        self.user.is_active = False
        self.user.save()

        payload = {"email": "test@example.com"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_format_returns_200(self):
        payload = {"email": "not-an-email"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)

    def test_missing_email_returns_200(self):
        payload = {}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)

    def test_email_normalization(self):
        payload = {"email": "TEST@EXAMPLE.COM"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        attempt = PasswordResetAttempt.objects.get(email='test@example.com')
        self.assertEqual(attempt.email, 'test@example.com')

    def test_rate_limiting_by_ip(self):
        payload = {"email": "test@example.com"}
        resp = self.client.post("/api/auth/password-reset/", payload, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_audit_log_tracks_ip(self):
        payload = {"email": "test@example.com"}

        resp = self.client.post(
            "/api/auth/password-reset/",
            payload,
            format="json",
            REMOTE_ADDR='192.168.1.1'
        )

        self.assertEqual(resp.status_code, 200)

        attempt = PasswordResetAttempt.objects.get(email='test@example.com')
        self.assertEqual(attempt.ip_address, '192.168.1.1')

    def test_multiple_users_same_ip(self):
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='TestPass123!',
            is_active=True,
        )

        resp1 = self.client.post(
            "/api/auth/password-reset/",
            {"email": "test@example.com"},
            format="json"
        )

        resp2 = self.client.post(
            "/api/auth/password-reset/",
            {"email": "test2@example.com"},
            format="json"
        )

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

        self.assertEqual(PasswordResetAttempt.objects.count(), 2)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetToken(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=True,
        )

    def test_token_generation(self):
        token = password_reset_token_generator.make_token(self.user)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertIn('-', token)

    def test_token_validation(self):
        token = password_reset_token_generator.make_token(self.user)
        is_valid = password_reset_token_generator.check_token(self.user, token)

        self.assertTrue(is_valid)

    def test_token_invalid_for_different_user(self):
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='TestPass123!',
        )

        token = password_reset_token_generator.make_token(self.user)
        is_valid = password_reset_token_generator.check_token(user2, token)

        self.assertFalse(is_valid)

    def test_token_invalid_format(self):
        is_valid = password_reset_token_generator.check_token(self.user, "invalid-token")

        self.assertFalse(is_valid)

    def test_empty_token(self):
        is_valid = password_reset_token_generator.check_token(self.user, "")

        self.assertFalse(is_valid)

    def test_none_token(self):
        is_valid = password_reset_token_generator.check_token(self.user, None)

        self.assertFalse(is_valid)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetEmailContent(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=True,
        )

    def test_email_contains_reset_link(self):
        payload = {"email": "test@example.com"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body

        self.assertIn('reset-password', email_body)
        self.assertIn('uid=', email_body)
        self.assertIn('token=', email_body)

    def test_email_has_correct_subject(self):
        payload = {"email": "test@example.com"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset', mail.outbox[0].subject)

    def test_email_mentions_expiry(self):
        payload = {"email": "test@example.com"}

        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body

        self.assertTrue(
            '1 hour' in email_body.lower() or
            'expire' in email_body.lower()
        )


class TestPasswordResetTokenTimeout(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
        )

    def test_token_uses_custom_timeout(self):
        self.assertEqual(password_reset_token_generator.timeout, 3600)

    @override_settings(PASSWORD_RESET_TIMEOUT=7200)
    def test_token_respects_settings_timeout(self):

        reload(tokens)

        self.assertEqual(tokens.password_reset_token_generator.timeout, 7200)

    def test_token_validation_basic(self):

        token = password_reset_token_generator.make_token(self.user)
        is_valid = password_reset_token_generator.check_token(self.user, token)

        self.assertTrue(is_valid)
