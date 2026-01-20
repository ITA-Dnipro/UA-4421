from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

import logging
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
