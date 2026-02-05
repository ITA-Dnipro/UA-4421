import logging
from django.utils import timezone
from django.db import transaction

from projects.models import Project, ModerationAction, ModerationStatus, ProjectModerationLog
from projects.services.email_service import ProjectModerationEmailService

logger = logging.getLogger(__name__)


class ProjectModerationService:

    @staticmethod
    @transaction.atomic
    def moderate_project(project, action, moderator, reason='', notes=''):
        old_status = project.moderation_status

        if action == ModerationAction.APPROVE:
            project.moderation_status = ModerationStatus.APPROVED
            project.moderated_by = moderator
            project.moderated_at = timezone.now()
            project.moderation_notes = notes
            project.rejection_reason = ''
            project.save(update_fields=[
                'moderation_status', 'moderated_by', 'moderated_at',
                'moderation_notes', 'rejection_reason'
            ])
            message = "Project approved successfully"

        elif action == ModerationAction.REJECT:
            if not reason:
                return False, "Rejection reason is required", project

            project.moderation_status = ModerationStatus.REJECTED
            project.moderated_by = moderator
            project.moderated_at = timezone.now()
            project.rejection_reason = reason
            project.moderation_notes = notes
            project.save(update_fields=[
                'moderation_status', 'moderated_by', 'moderated_at',
                'rejection_reason', 'moderation_notes'
            ])

            try:
                ProjectModerationEmailService.send_rejection_email(project, reason)
            except Exception as e:
                logger.error(f"Failed to send rejection email: {e}")

            message = "Project rejected and owner notified"

        elif action == ModerationAction.FLAG:
            project.moderation_status = ModerationStatus.FLAGGED
            project.moderated_by = moderator
            project.moderated_at = timezone.now()
            project.moderation_notes = f"{notes}\nFlagged: {reason}".strip() if reason else notes
            project.save(update_fields=[
                'moderation_status', 'moderated_by', 'moderated_at', 'moderation_notes'
            ])
            message = "Project flagged for review"

        else:
            return False, f"Invalid action: {action}", project

        ProjectModerationLog.objects.create(
            project=project,
            action=action,
            moderator=moderator,
            reason=reason,
            notes=notes,
            old_status=old_status,
            new_status=project.moderation_status
        )

        logger.info(f"Project {project.id} moderated: {action} by {moderator.username}")
        return True, message, project
