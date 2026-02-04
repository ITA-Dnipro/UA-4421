import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


class ProjectModerationEmailService:

    @staticmethod
    def send_rejection_email(project, reason):
        try:
            startup_user = project.startup_profile.user

            context = {
                'user_name': startup_user.first_name or startup_user.username,
                'project_title': project.title,
                'project_slug': project.slug,
                'reason': reason,
                'company_name': project.startup_profile.company_name,
                'site_name': getattr(settings, 'SITE_NAME', 'Startup Gateway'),
                'support_email': settings.DEFAULT_FROM_EMAIL,
                'dashboard_url': f"{settings.FRONTEND_URL}/dashboard/projects",
            }

            subject = f'Project "{project.title}" Requires Attention'

            html_message = render_to_string(
                'emails/project_rejection.html',
                context
            )
            plain_message = render_to_string(
                'emails/project_rejection.txt',
                context
            )

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[startup_user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(
                f"Rejection email sent to {startup_user.email} "
                f"for project {project.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send rejection email for project {project.id}: {e}"
            )
            return False
