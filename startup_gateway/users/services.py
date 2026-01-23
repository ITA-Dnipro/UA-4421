
import logging
import uuid

from investors.models import InvestorProfile
from startups.models import StartupProfile
from users.models import Role

from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

logger = logging.getLogger(__name__)

User = get_user_model()


def build_email_verification_token(user):
    signer = TimestampSigner(salt="users.email.verify")
    payload = f"{user.pk}:{user.email.strip().lower()}"
    return signer.sign(payload)


def build_email_verification_url(token):
    base = getattr(settings, "APP_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/api/auth/verify-email/?token={token}"


def send_verification_email(user):
    token = build_email_verification_token(user)
    url = build_email_verification_url(token)

    try:
        send_mail(
            subject="Verify your email",
            message=f"Open this link to verify your email: {url}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send verification email")

    return token


def verify_email_token(token):
    signer = TimestampSigner(salt="users.email.verify")
    max_age = getattr(settings, "EMAIL_VERIFICATION_TOKEN_MAX_AGE", 60 * 60 * 24)

    try:
        payload = signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

    try:
        user_id_str, email = payload.split(":", 1)
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        return None

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return None

    if user.email.strip().lower() != email.strip().lower():
        return None

    if (not user.verified) or (not user.is_active):
        user.verified = True
        user.is_active = True
        user.save(update_fields=["verified", "is_active"])

    return user

@transaction.atomic
def register_user(validated_data, user_model):
    email = validated_data["email"].strip().lower()
    role_name = validated_data["role"].strip().lower()
    company_name = validated_data["company_name"]
    short_pitch = validated_data.get("short_pitch", "")
    website = validated_data.get("website", "")
    phone = validated_data.get("contact_phone", "")

    existing = user_model.objects.filter(email__iexact=email).first()
    if existing:
        should_send_email = not getattr(existing, "verified", False)
        return existing, False, should_send_email

    user = user_model(
        username=uuid.uuid4().hex,
        email=email,
        phone=phone,
        verified=False,
        is_active=False,
    )
    user.set_password(validated_data["password"])
    user.save()

    role_obj, _ = Role.objects.get_or_create(name=role_name)
    user.roles.add(role_obj)

    if role_name == "startup":
        StartupProfile.objects.create(
            user=user,
            company_name=company_name,
            short_pitch=short_pitch,
            website=website,
        )
    else:
        InvestorProfile.objects.create(
            user=user,
            company_name=company_name,
        )

    return user, True, True

