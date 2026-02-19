import json
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.signing import SignatureExpired, TimestampSigner
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import authenticate
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from importlib import reload
from datetime import timedelta

from startups.models import StartupProfile
from investors.models import InvestorProfile
from users.models import PasswordResetAttempt, Role, PasswordResetConfirmation
from users.tokens import password_reset_token_generator
from users.email_service import PasswordResetEmailService
from users import tokens
from users.authentication import VersionedJWTAuthentication

User = get_user_model()

class TestJWTVersionInvalidation(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="OldPass123!",
            is_active=True,
        )

    def test_jwt_invalid_after_password_change(self):
        
        token = AccessToken.for_user(self.user)

        
        auth = VersionedJWTAuthentication()
        user_from_token = auth.get_user(token)
        self.assertEqual(user_from_token, self.user)

        
        self.user.set_password("NewPass123!")
        self.user.jwt_version += 1  
        self.user.save()

        
        with self.assertRaisesMessage(
            Exception, "Your session has been invalidated"
        ):
            auth.get_user(token)



@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestRegisterApi(APITestCase):
    def setUp(self):
        super().setUp()
        # створюємо ролі для тестової бази
        Role.objects.get_or_create(name="startup")
        Role.objects.get_or_create(name="investor")
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

    def test_email_verification_nonce_is_hashed(self):
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

        raw_nonce = token.split(":", 4)[2]

        user = User.objects.get(email="alice@example.com")
        self.assertNotEqual(user.email_verification_nonce, raw_nonce)
        self.assertTrue(user.email_verification_nonce)

    
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
    def setUp(self):
        super().setUp()
        Role.objects.get_or_create(name="startup")
        Role.objects.get_or_create(name="investor")
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

    def test_verify_email_rejects_legacy_token_without_nonce(self):
        payload = {
            "email": "alice@example.com",
            "password": "P@ssw0rd!123",
            "role": "startup",
            "company_name": "Handmade Co",
        }

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(resp.status_code, 201)

        user = User.objects.get(email="alice@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.verified)

        signer = TimestampSigner(salt="users.email.verify")
        legacy_token = signer.sign(f"{user.pk}:{user.email.strip().lower()}")

        verify_resp = self.client.post("/api/auth/verify-email/", {"token": legacy_token}, format="json")
        self.assertEqual(verify_resp.status_code, 400)

        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertFalse(user.verified)

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


    def test_resend_non_existing_email_does_not_set_email_cache_key(self):
        self.client.post(
            "/api/auth/resend-verification/",
            {"email": "missing@example.com"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertIsNone(cache.get("auth:resend-verification:email:missing@example.com"))


    def test_resend_non_existing_email_sets_ip_cache_key(self):
        self.client.post(
            "/api/auth/resend-verification/",
            {"email": "missing@example.com"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertTrue(cache.get("auth:resend-verification:ip:10.0.0.1"))


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
        self.assertIn(':', token)

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

    def test_tampered_token_fails(self):
        token = password_reset_token_generator.make_token(self.user)

        tampered = token[:-5] + "xxxxx"

        is_valid = password_reset_token_generator.check_token(self.user, tampered)
        self.assertFalse(is_valid)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetEmailErrors(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=True,
        )

    @patch('users.email_service.send_mail')
    def test_email_service_handles_send_failure(self, mock_send):

        mock_send.side_effect = Exception("SMTP server error")

        token = password_reset_token_generator.make_token(self.user)
        result = PasswordResetEmailService.send_reset_email(
            user=self.user,
            token=token,
            request=None
        )

        self.assertFalse(result)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetAuditErrors(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=True,
        )

    @patch('users.models.PasswordResetAttempt.objects.create')
    def test_continues_when_audit_log_fails(self, mock_create):
        mock_create.side_effect = Exception("Database error")

        payload = {"email": "test@example.com"}
        resp = self.client.post("/api/auth/password-reset/", payload, format="json")

        self.assertEqual(resp.status_code, 200)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetAttemptModel(APITestCase):

    def test_str_representation(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
        )

        attempt = PasswordResetAttempt.objects.create(
            user=user,
            email='test@example.com',
            ip_address='192.168.1.1',
            token_sent=True,
        )

        str_repr = str(attempt)
        self.assertIn('test@example.com', str_repr)
        self.assertIn('Reset attempt', str_repr)


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


@override_settings(
    AXES_ENABLED=True,
    AXES_FAILURE_LIMIT=5,
    AXES_COOLOFF_TIME=timedelta(minutes=5),
    AXES_USERNAME_FORM_FIELD="email",
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    },
)
class TestLoginApi(APITestCase):
    def setUp(self):
        super().setUp()
        self.user_password = "P@ssw0rd!123"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.user_password,
            is_active=True,
            verified=True,
        )

        self.url = "/api/auth/login/"
        self.ip = "10.0.0.1"

    def _json(self, resp):
        if hasattr(resp, "data"):
            return resp.data
        return json.loads(resp.content.decode("utf-8"))

    def _ttl_seconds_from_token(self, token_str: str, token_cls):
        token = token_cls(token_str)
        exp = int(token["exp"])
        iat = int(token["iat"])
        return exp - iat

    def _assert_ttl_close(self, actual_seconds: int, expected: timedelta, tolerance_seconds: int = 5):
        expected_seconds = int(expected.total_seconds())
        self.assertTrue(
            abs(actual_seconds - expected_seconds) <= tolerance_seconds,
            msg=f"TTL mismatch: got {actual_seconds}s, expected {expected_seconds}s ±{tolerance_seconds}s",
        )

    def test_login_success_returns_tokens_and_user(self):
        payload = {
            "email": self.user.email,
            "password": self.user_password,
        }

        resp = self.client.post(self.url, payload, format="json", REMOTE_ADDR=self.ip)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertIn("user", resp.data)
        self.assertEqual(resp.data["user"]["email"], self.user.email)

    def test_login_success_with_remember_returns_tokens(self):
        payload = {
            "email": self.user.email,
            "password": self.user_password,
            "remember": True,
        }

        resp = self.client.post(self.url, payload, format="json", REMOTE_ADDR=self.ip)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], self.user.email)

    def test_login_invalid_credentials_returns_401(self):
        payload = {
            "email": self.user.email,
            "password": "wrong-password",
        }

        resp = self.client.post(self.url, payload, format="json", REMOTE_ADDR=self.ip)

        self.assertEqual(resp.status_code, 401)
        self.assertTrue("detail" in resp.data or "non_field_errors" in resp.data)

    def test_login_lockout_after_repeated_failures_returns_429(self):
        for _ in range(4):
            resp = self.client.post(
                self.url,
                {"email": self.user.email, "password": "wrong"},
                format="json",
                REMOTE_ADDR=self.ip,
            )
            self.assertEqual(resp.status_code, 401)
        locked = self.client.post(
            self.url,
            {"email": self.user.email, "password": "wrong"},
            format="json",
            REMOTE_ADDR=self.ip,
        )
        self.assertEqual(locked.status_code, 429)
        data = self._json(locked)
        self.assertIn("detail", data)

    def test_login_during_lockout_blocks_even_with_correct_password(self):
        for _ in range(5):
            self.client.post(
                self.url,
                {"email": self.user.email, "password": "wrong"},
                format="json",
                REMOTE_ADDR=self.ip,
            )
        resp = self.client.post(
            self.url,
            {"email": self.user.email, "password": self.user_password},
            format="json",
            REMOTE_ADDR=self.ip,
        )
        self.assertEqual(resp.status_code, 429)
        data = self._json(resp)
        self.assertIn("detail", data)

    def test_remember_true_changes_access_and_refresh_ttl(self):
        payload = {"email": self.user.email, "password": self.user_password, "remember": True}
        resp = self.client.post(self.url, payload, format="json", REMOTE_ADDR=self.ip)
        self.assertEqual(resp.status_code, 200)

        access_ttl = self._ttl_seconds_from_token(resp.data["access"], AccessToken)
        refresh_ttl = self._ttl_seconds_from_token(resp.data["refresh"], RefreshToken)

        self._assert_ttl_close(access_ttl, timedelta(minutes=30))
        self._assert_ttl_close(refresh_ttl, timedelta(days=7))

    def test_default_ttl_matches_simplejwt_settings_when_remember_not_set(self):
        payload = {"email": self.user.email, "password": self.user_password}
        resp = self.client.post(self.url, payload, format="json", REMOTE_ADDR=self.ip)
        self.assertEqual(resp.status_code, 200)

        access_ttl = self._ttl_seconds_from_token(resp.data["access"], AccessToken)
        refresh_ttl = self._ttl_seconds_from_token(resp.data["refresh"], RefreshToken)

        simple_jwt = getattr(settings, "SIMPLE_JWT", {})
        expected_access = simple_jwt.get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=5))
        expected_refresh = simple_jwt.get("REFRESH_TOKEN_LIFETIME", timedelta(days=1))

        self._assert_ttl_close(access_ttl, expected_access)
        self._assert_ttl_close(refresh_ttl, expected_refresh)

    def test_default_ttl_not_violated_even_if_remember_false(self):
        payload = {"email": self.user.email, "password": self.user_password, "remember": False}
        resp = self.client.post(self.url, payload, format="json", REMOTE_ADDR=self.ip)
        self.assertEqual(resp.status_code, 200)

        access_ttl = self._ttl_seconds_from_token(resp.data["access"], AccessToken)
        refresh_ttl = self._ttl_seconds_from_token(resp.data["refresh"], RefreshToken)

        simple_jwt = getattr(settings, "SIMPLE_JWT", {})
        expected_access = simple_jwt.get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=5))
        expected_refresh = simple_jwt.get("REFRESH_TOKEN_LIFETIME", timedelta(days=1))

        self._assert_ttl_close(access_ttl, expected_access)
        self._assert_ttl_close(refresh_ttl, expected_refresh)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestPasswordResetConfirm(APITestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPass123!',
            is_active=True,
        )
        self.url = '/api/auth/password-reset/confirm/'

    def tearDown(self):
        cache.clear()

    def test_valid_token_changes_password(self):


        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['detail'], "Password changed successfully.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewP@ssw0rd123"))
        self.assertFalse(self.user.check_password("OldPass123!"))

        confirmation = PasswordResetConfirmation.objects.get(user=self.user)
        self.assertTrue(confirmation.success)

    def test_invalid_token_returns_400(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": "invalid-token-12345",
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], "Invalid or expired password reset link.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass123!"))

    def test_invalid_uid_returns_400(self):
        token = password_reset_token_generator.make_token(self.user)

        payload = {
            "uid": "invalid-uid",
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], "Invalid or expired password reset link.")

    def test_weak_password_returns_422(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 422)
        self.assertIn('password', resp.data)

    def test_missing_fields_returns_422(self):
        resp = self.client.post(self.url, {
            "uid": "MQ",
            "password": "NewP@ssw0rd123"
        }, format="json")
        self.assertEqual(resp.status_code, 400)

        resp = self.client.post(self.url, {
            "token": "abc123",
            "password": "NewP@ssw0rd123"
        }, format="json")
        self.assertEqual(resp.status_code, 400)

        resp = self.client.post(self.url, {
            "uid": "MQ",
            "token": "abc123"
        }, format="json")
        self.assertEqual(resp.status_code, 422)

    def test_token_for_different_user_fails(self):
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='OldPass123!',
        )

        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(user2.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)

        user2.refresh_from_db()
        self.assertTrue(user2.check_password("OldPass123!"))

    def test_user_can_login_with_new_password(self):
        from django.test import RequestFactory

        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('detail', resp.data)

        request = RequestFactory().post('/api/auth/login/')
        user = authenticate(request=request, username='testuser', password='NewP@ssw0rd123')
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

        user = authenticate(request=request, username='testuser', password='OldPass123!')
        self.assertIsNone(user)

    def test_audit_log_tracks_ip(self):


        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(
            self.url,
            payload,
            format="json",
            REMOTE_ADDR='192.168.1.100'
        )

        self.assertEqual(resp.status_code, 200)

        confirmation = PasswordResetConfirmation.objects.get(user=self.user)
        self.assertEqual(confirmation.ip_address, '192.168.1.100')

    def test_model_str_representation(self):
        confirmation = PasswordResetConfirmation.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            success=True
        )

        str_repr = str(confirmation)
        self.assertIn(self.user.username, str_repr)
        self.assertIn('Password reset', str_repr)

    def test_nonexistent_user_id_in_uid(self):
        uid = urlsafe_base64_encode(force_bytes(99999))
        token = "any-token"

        payload = {"uid": uid, "token": token, "password": "NewP@ssw0rd123"}
        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)

    def test_token_cannot_be_reused(self):
        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {"uid": uid, "token": token, "password": "NewP@ssw0rd123"}

        self.client.post(self.url, payload, format="json")
        resp2 = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp2.status_code, 400)

    @patch('users.models.PasswordResetConfirmation.objects.create')
    def test_handles_audit_log_failure(self, mock_create):
        mock_create.side_effect = Exception("DB error")

        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {"uid": uid, "token": token, "password": "NewP@ssw0rd123"}
        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewP@ssw0rd123"))

    def test_token_invalid_after_password_change(self):
        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        self.assertTrue(password_reset_token_generator.check_token(self.user, token))

        self.user.set_password("DifferentPassword123!")
        self.user.save()

        self.assertFalse(password_reset_token_generator.check_token(self.user, token))

        payload = {
            "uid": uid,
            "token": token,
            "password": "HackerPassword123!"
        }

        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)


class TestPasswordResetConfirmAuditLogging(APITestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPass123!',
            is_active=True,
        )
        self.url = '/api/auth/password-reset/confirm/'

    def test_logs_failed_attempt_with_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": "invalid-token-12345",
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(
            self.url,
            payload,
            format="json",
            REMOTE_ADDR='192.168.1.100'
        )

        self.assertEqual(resp.status_code, 400)

        confirmation = PasswordResetConfirmation.objects.filter(
            user=self.user,
            success=False
        ).first()

        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.ip_address, '192.168.1.100')
        self.assertEqual(confirmation.failure_reason, 'invalid_token')

    def test_logs_failed_attempt_with_invalid_uid(self):
        token = password_reset_token_generator.make_token(self.user)

        payload = {
            "uid": "invalid-uid",
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(
            self.url,
            payload,
            format="json",
            REMOTE_ADDR='192.168.1.101'
        )

        self.assertEqual(resp.status_code, 400)

        confirmation = PasswordResetConfirmation.objects.filter(
            success=False,
            ip_address='192.168.1.101'
        ).first()

        self.assertIsNotNone(confirmation)
        self.assertIsNone(confirmation.user)
        self.assertEqual(confirmation.failure_reason, 'invalid_uid_format')

    def test_logs_failed_attempt_with_weak_password(self):
        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "123"
        }

        resp = self.client.post(
            self.url,
            payload,
            format="json",
            REMOTE_ADDR='192.168.1.102'
        )

        self.assertEqual(resp.status_code, 422)

        confirmation = PasswordResetConfirmation.objects.filter(
            user=self.user,
            success=False
        ).first()

        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.failure_reason, 'weak_password')

    def test_logs_successful_attempt(self):
        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(
            self.url,
            payload,
            format="json",
            REMOTE_ADDR='192.168.1.103'
        )

        self.assertEqual(resp.status_code, 200)

        confirmation = PasswordResetConfirmation.objects.filter(
            user=self.user,
            success=True
        ).first()

        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.ip_address, '192.168.1.103')
        self.assertIsNone(confirmation.failure_reason)

    def test_can_detect_brute_force_attempts(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        for i in range(5):
            self.client.post(
                self.url,
                {
                    "uid": uid,
                    "token": f"invalid-token-{i}",
                    "password": "NewP@ssw0rd123"
                },
                format="json",
                REMOTE_ADDR='192.168.1.200'
            )

        failed_attempts = PasswordResetConfirmation.objects.filter(
            ip_address='192.168.1.200',
            success=False
        )

        self.assertEqual(failed_attempts.count(), 5)

        for attempt in failed_attempts:
            self.assertEqual(attempt.user, self.user)
            self.assertEqual(attempt.failure_reason, 'invalid_token')


class TestPasswordResetSecurityMessages(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPass123!',
            is_active=True,
        )
        self.url = '/api/auth/password-reset/confirm/'

    def test_invalid_uid_gives_generic_error(self):
        payload = {
            "uid": "invalid-uid",
            "token": "any-token",
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertNotIn('user', str(resp.data).lower())
        self.assertNotIn('uid', str(resp.data).lower())
        self.assertIn('invalid or expired', str(resp.data).lower())

    def test_nonexistent_user_gives_generic_error(self):
        uid = urlsafe_base64_encode(force_bytes(99999))

        payload = {
            "uid": uid,
            "token": "any-token",
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertNotIn('not found', str(resp.data).lower())
        self.assertNotIn('does not exist', str(resp.data).lower())
        self.assertIn('invalid or expired', str(resp.data).lower())

    def test_invalid_token_gives_generic_error(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": "invalid-token",
            "password": "NewP@ssw0rd123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.data.get('detail'),
            "Invalid or expired password reset link."
        )

    def test_weak_password_gives_specific_error(self):
        token = password_reset_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        payload = {
            "uid": uid,
            "token": token,
            "password": "123"
        }

        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 422)
        self.assertIn('password', resp.data)
        self.assertNotIn('detail', resp.data)

    def test_all_failure_types_look_identical_to_attacker(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        test_cases = [
            ("invalid_uid", {"uid": "bad", "token": "x", "password": "P@ssw0rd123"}),
            ("nonexistent_user",
             {"uid": urlsafe_base64_encode(force_bytes(99999)), "token": "x", "password": "P@ssw0rd123"}),
            ("invalid_token", {"uid": uid, "token": "bad-token", "password": "P@ssw0rd123"}),
        ]

        responses = []
        for desc, payload in test_cases:
            resp = self.client.post(self.url, payload, format="json")
            responses.append(resp.data.get('detail', str(resp.data)))

        self.assertEqual(len(set(responses)), 1, "Different errors revealed different messages!")
        self.assertIn('invalid or expired', responses[0].lower())

    def test_audit_log_still_tracks_specific_error_types(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        resp = self.client.post(
            self.url,
            {"uid": uid, "token": "bad-token", "password": "P@ssw0rd123"},
            format="json",
            REMOTE_ADDR='192.168.1.100'
        )

        self.assertEqual(resp.status_code, 400)

        confirmation = PasswordResetConfirmation.objects.filter(
            ip_address='192.168.1.100'
        ).first()

        self.assertIsNotNone(confirmation)
        self.assertFalse(confirmation.success)
        self.assertEqual(confirmation.failure_reason, 'invalid_token')
        self.assertEqual(confirmation.user, self.user)
