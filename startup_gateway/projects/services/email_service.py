import logging
from django.template.loader import render_to_string
from django.core.mail import send_mail
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
                'rejection_reason': reason,
                'project_url': f"{settings.APP_BASE_URL}/dashboard/projects/{project.id}",
                'site_name': getattr(settings, 'SITE_NAME', 'Startup Gateway'),
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }

            # Отримати HTML та текстовий контент
            html_message = render_to_string('emails/rejection.html', context)
            text_message = render_to_string('emails/rejection.txt', context)

            send_mail(
                subject=f'Ваш проект "{project.title}" не пройшов модерацію',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[startup_user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Rejection email sent to {startup_user.email} for project {project.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send rejection email for project {project.id}: {str(e)}")
            raise
