from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import logging

logger = logging.getLogger(__name__)


class PasswordResetEmailService:
    @staticmethod
    def send_reset_email(user, token, request=None):
        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                domain = getattr(settings, 'FRONTEND_URL', 'localhost:3000')
                protocol = 'https' if 'localhost' not in domain else 'http'

            reset_link = f"{protocol}://{domain}/reset-password?uid={uid}&token={token}"

            context = {
                'user': user,
                'reset_link': reset_link,
                'expiry_hours': 1,
                'site_name': getattr(settings, 'SITE_NAME', 'Startup Gateway'),
            }

            subject = 'Password Reset Request - Startup Gateway'
            html_message = render_to_string('emails/password_reset.html', context)
            plain_message = render_to_string('emails/password_reset.txt', context)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Password reset email sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send reset email to {user.email}: {e}")
            return False
