import logging
import uuid
from django.core.cache import cache

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
    user.email_verification_nonce = uuid.uuid4().hex
    user.save(update_fields=["email_verification_nonce"])
    payload = f"{user.pk}:{user.email.strip().lower()}:{user.email_verification_nonce}"
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

    parts = payload.split(":", 2)
    if len(parts) not in (2, 3):
        return None

    try:
        user_id = int(parts[0])
    except (ValueError, TypeError):
        return None

    email = parts[1]
    nonce = parts[2] if len(parts) == 3 else None

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return None

    if user.email.strip().lower() != email.strip().lower():
        return None

    if nonce is not None:
        if not user.email_verification_nonce:
            return None
        if user.email_verification_nonce != nonce:
            return None

    update_fields = []
    if not user.verified:
        user.verified = True
        update_fields.append("verified")
    if not user.is_active:
        user.is_active = True
        update_fields.append("is_active")

    if nonce is not None:
        user.email_verification_nonce = ""
        update_fields.append("email_verification_nonce")

    if update_fields:
        user.save(update_fields=update_fields)

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


def _resend_verification_email_key(email: str) -> str:
    return f"auth:resend-verification:email:{email}"


def _resend_verification_ip_key(ip: str) -> str:
    return f"auth:resend-verification:ip:{ip}"


def is_resend_verification_throttled(email: str, ip: str) -> bool:
    email = (email or "").strip().lower()
    ip = (ip or "").strip()

    email_ttl = int(getattr(settings, "EMAIL_VERIFICATION_RESEND_EMAIL_TTL", 60))
    ip_ttl = int(getattr(settings, "EMAIL_VERIFICATION_RESEND_IP_TTL", 60))

    email_key = _resend_verification_email_key(email) if email else ""
    ip_key = _resend_verification_ip_key(ip) if ip else ""

    if email_key and cache.get(email_key):
        return True
    if ip_key and cache.get(ip_key):
        return True

    if email_key:
        cache.set(email_key, 1, timeout=email_ttl)
    if ip_key:
        cache.set(ip_key, 1, timeout=ip_ttl)

    return False
