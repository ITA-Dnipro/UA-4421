import logging

from celery import shared_task
from django.db import IntegrityError
from django.contrib.auth import get_user_model

from projects.models import Project
from notifications.models import Notification
from dashboard.models import SavedStartup

logger = logging.getLogger(__name__)
User = get_user_model()

# Email stubs
def build_project_created_email(project, user):
    subject = f"Project launched: {project.title}"
    body = f"Hello {user.email}, the project '{project.title}' has just been created."
    return subject, body

def build_project_fundraising_email(project, user):
    subject = f"Project fundraising started: {project.title}"
    body = f"Hello {user.email}, the project '{project.title}' is now in fundraising stage."
    return subject, body

def build_project_funded_email(project, user):
    subject = f"Project funded: {project.title}"
    body = f"Hello {user.email}, the project '{project.title}' has been funded!"
    return subject, body

# Main task
@shared_task(autoretry_for=(Exception,), retry_backoff=5)
def handle_project_event(event_type, project_id, payload):
    try:
        project = (
            Project.objects
            .select_related("startup_profile")
            .get(id=project_id)
        )
    except Project.DoesNotExist:
        logger.warning("Notification task skipped: project %s does not exist", project_id)
        return

    recipients = get_recipients(project)

    for user in recipients:
        event_key = f"{event_type}:{project.id}:{user.id}"

        try:
            Notification.objects.create(
                user=user,
                project=project,
                type=event_type,
                payload={
                    "project_id": str(project.id),
                    **payload,
                },
                event_key=event_key,
            )
        except IntegrityError:
            logger.info("Notification already exists (event_key=%s)", event_key)
        except Exception as exc:
            logger.error(
                "Failed to create notification (event_type=%s, project_id=%s, user_id=%s): %s",
                event_type,
                project.id,
                user.id,
                exc,
            )
            raise

        # Email stub logging
        subject = body = None
        if event_type == "project_created":
            subject, body = build_project_created_email(project, user)
        elif event_type == "project_status_changed" and payload.get("new_status") == "active":
            subject, body = build_project_fundraising_email(project, user)
        elif event_type == "project_status_changed" and payload.get("new_status") == "funded":
            subject, body = build_project_funded_email(project, user)

        if subject and body:
            logger.info("EMAIL STUB | to=%s | subject=%s | body=%s", user.email, subject, body)


def get_recipients(project):
    """
    Resolve users who should receive notifications for project events.
    Path: Project -> StartupProfile -> SavedStartup -> InvestorProfile -> User
    """
    user_ids = (
        SavedStartup.objects
        .filter(startup_profile=project.startup_profile)
        .select_related("investor_profile__user")
        .values_list("investor_profile__user_id", flat=True)
    )

    return User.objects.filter(id__in=user_ids)

