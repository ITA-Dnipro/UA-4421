import logging
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from projects.models import (
    Project, ProjectModerationLog, ProjectModerationStats,
    ModerationAction, ModerationStatus
)
from projects.services.email_service import ProjectModerationEmailService

logger = logging.getLogger(__name__)


class ProjectModerationService:

    @staticmethod
    @transaction.atomic
    def moderate_project(project, action, moderator, reason='', notes='', request=None):
        old_status = project.moderation_status

        if action == ModerationAction.APPROVE:
            success, message = ProjectModerationService._approve_project(
                project, moderator, notes
            )
        elif action == ModerationAction.REJECT:
            success, message = ProjectModerationService._reject_project(
                project, moderator, reason, notes
            )
        elif action == ModerationAction.FLAG:
            success, message = ProjectModerationService._flag_project(
                project, moderator, reason, notes
            )
        elif action == ModerationAction.RESTORE:
            success, message = ProjectModerationService._restore_project(
                project, moderator, notes
            )
        elif action == ModerationAction.DELETE:
            success, message = ProjectModerationService._delete_project(
                project, moderator, reason, notes
            )
        else:
            return False, f"Invalid action: {action}", project

        if not success:
            return False, message, project

        metadata = {}
        if request:
            metadata = {
                'ip_address': ProjectModerationService._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }

        ProjectModerationLog.objects.create(
            project=project,
            action=action,
            moderator=moderator,
            reason=reason,
            notes=notes,
            old_status=old_status,
            new_status=project.moderation_status,
            metadata=metadata
        )

        ProjectModerationService._update_stats(action)

        ProjectModerationService._invalidate_cache(project)

        logger.info(
            f"Project {project.id} moderated: {action} by {moderator.username}"
        )

        return True, message, project

    @staticmethod
    def _approve_project(project, moderator, notes):
        if project.moderation_status == ModerationStatus.APPROVED:
            return False, "Project is already approved"

        if project.is_deleted:
            return False, "Cannot approve deleted project. Restore it first."

        project.moderation_status = ModerationStatus.APPROVED
        project.moderated_by = moderator
        project.moderated_at = timezone.now()
        project.moderation_notes = notes
        project.rejection_reason = ''
        project.save(update_fields=[
            'moderation_status', 'moderated_by', 'moderated_at',
            'moderation_notes', 'rejection_reason'
        ])

        return True, "Project approved successfully"

    @staticmethod
    def _reject_project(project, moderator, reason, notes):
        if not reason:
            return False, "Rejection reason is required"

        if project.is_deleted:
            return False, "Cannot reject deleted project"

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
            email_sent = ProjectModerationEmailService.send_rejection_email(
                project=project,
                reason=reason
            )
            if not email_sent:
                logger.warning(f"Failed to send rejection email for project {project.id}")
        except Exception as e:
            logger.error(f"Error sending rejection email: {e}")

        return True, "Project rejected and owner notified"

    @staticmethod
    def _flag_project(project, moderator, reason, notes):
        if project.is_deleted:
            return False, "Cannot flag deleted project"

        project.moderation_status = ModerationStatus.FLAGGED
        project.moderated_by = moderator
        project.moderated_at = timezone.now()
        project.moderation_notes = f"{notes}\nFlagged: {reason}".strip()
        project.save(update_fields=[
            'moderation_status', 'moderated_by', 'moderated_at',
            'moderation_notes'
        ])

        return True, "Project flagged for review"

    @staticmethod
    def _restore_project(project, moderator, notes):
        if not project.is_deleted:
            return False, "Project is not deleted"

        project.is_deleted = False
        project.deleted_at = None
        project.deleted_by = None
        project.moderation_status = ModerationStatus.PENDING
        project.moderated_by = moderator
        project.moderated_at = timezone.now()
        project.moderation_notes = notes
        project.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by',
            'moderation_status', 'moderated_by', 'moderated_at',
            'moderation_notes'
        ])

        return True, "Project restored successfully"

    @staticmethod
    def _delete_project(project, moderator, reason, notes):
        if project.is_deleted:
            return False, "Project is already deleted"

        project.is_deleted = True
        project.deleted_at = timezone.now()
        project.deleted_by = moderator
        project.moderation_notes = f"{notes}\nDeleted: {reason}".strip()
        project.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by', 'moderation_notes'
        ])

        return True, "Project deleted successfully"

    @staticmethod
    def _update_stats(action):
        from django.db.models import F

        today = timezone.now().date()
        stats, created = ProjectModerationStats.objects.get_or_create(date=today)

        field_map = {
            ModerationAction.APPROVE: 'approved_count',
            ModerationAction.REJECT: 'rejected_count',
            ModerationAction.FLAG: 'flagged_count',
            ModerationAction.DELETE: 'deleted_count',
            ModerationAction.RESTORE: 'restored_count',
        }

        field = field_map.get(action)
        if field:
            setattr(stats, field, F(field) + 1)
            stats.save(update_fields=[field])

    @staticmethod
    def _invalidate_cache(project):
        cache_keys = [
            f'project:{project.id}',
            f'project:slug:{project.slug}',
            f'startup:{project.startup_profile.id}:projects',
        ]
        cache.delete_many(cache_keys)

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
