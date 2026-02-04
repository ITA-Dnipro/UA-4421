from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from tabulate import tabulate

from projects.models import Project, ModerationStatus, ModerationAction
from projects.moderation_service import ProjectModerationService

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage project moderation from CLI'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands')

        list_parser = subparsers.add_parser('list', help='List projects')
        list_parser.add_argument(
            '--status',
            choices=['pending', 'approved', 'rejected', 'flagged'],
            help='Filter by moderation status'
        )
        list_parser.add_argument('--limit', type=int, default=50)

        approve_parser = subparsers.add_parser('approve', help='Approve project')
        approve_parser.add_argument('project_id', type=int)
        approve_parser.add_argument('--notes', type=str, default='')
        approve_parser.add_argument('--admin-email', type=str, help='Admin email')

        reject_parser = subparsers.add_parser('reject', help='Reject project')
        reject_parser.add_argument('project_id', type=int)
        reject_parser.add_argument('--reason', type=str, required=True)
        reject_parser.add_argument('--notes', type=str, default='')
        reject_parser.add_argument('--admin-email', type=str, help='Admin email')

        flag_parser = subparsers.add_parser('flag', help='Flag project')
        flag_parser.add_argument('project_id', type=int)
        flag_parser.add_argument('--reason', type=str, required=True)
        flag_parser.add_argument('--admin-email', type=str, help='Admin email')

        subparsers.add_parser('stats', help='Show moderation statistics')

        cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old deleted projects')
        cleanup_parser.add_argument('--days', type=int, default=30)

    def handle(self, *args, **options):
        subcommand = options.get('subcommand')

        if subcommand == 'list':
            self.list_projects(options)
        elif subcommand == 'approve':
            self.approve_project(options)
        elif subcommand == 'reject':
            self.reject_project(options)
        elif subcommand == 'flag':
            self.flag_project(options)
        elif subcommand == 'stats':
            self.show_stats()
        elif subcommand == 'cleanup':
            self.cleanup_deleted(options)
        else:
            self.print_help('manage.py', 'moderate_projects')

    def list_projects(self, options):
        queryset = Project.objects.select_related(
            'startup_profile',
            'moderated_by'
        ).all()

        status_filter = options.get('status')
        if status_filter:
            queryset = queryset.filter(moderation_status=status_filter)

        queryset = queryset.order_by('-created_at')[:options['limit']]

        if not queryset.exists():
            self.stdout.write(self.style.WARNING('No projects found'))
            return

        table_data = []
        for project in queryset:
            table_data.append([
                project.id,
                project.title[:40],
                project.startup_profile.company_name[:30],
                project.moderation_status,
                'Yes' if project.is_deleted else 'No',
                project.created_at.strftime('%Y-%m-%d'),
                project.moderated_by.username if project.moderated_by else '-'
            ])

        headers = ['ID', 'Title', 'Startup', 'Status', 'Deleted', 'Created', 'Moderated By']
        self.stdout.write('\n' + tabulate(table_data, headers=headers, tablefmt='grid'))
        self.stdout.write(f'\nTotal: {len(table_data)} projects')

    def approve_project(self, options):
        project_id = options['project_id']
        notes = options['notes']
        admin = self._get_admin(options.get('admin_email'))

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Project {project_id} not found'))
            return

        success, message, _ = ProjectModerationService.moderate_project(
            project=project,
            action=ModerationAction.APPROVE,
            moderator=admin,
            notes=notes
        )

        if success:
            self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ {message}'))

    def reject_project(self, options):
        project_id = options['project_id']
        reason = options['reason']
        notes = options['notes']
        admin = self._get_admin(options.get('admin_email'))

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Project {project_id} not found'))
            return

        success, message, _ = ProjectModerationService.moderate_project(
            project=project,
            action=ModerationAction.REJECT,
            moderator=admin,
            reason=reason,
            notes=notes
        )

        if success:
            self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ {message}'))

    def flag_project(self, options):
        project_id = options['project_id']
        reason = options['reason']
        admin = self._get_admin(options.get('admin_email'))

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Project {project_id} not found'))
            return

        success, message, _ = ProjectModerationService.moderate_project(
            project=project,
            action=ModerationAction.FLAG,
            moderator=admin,
            reason=reason
        )

        if success:
            self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ {message}'))

    def show_stats(self):
        from django.db.models import Count, Q

        stats = Project.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(moderation_status=ModerationStatus.PENDING)),
            approved=Count('id', filter=Q(moderation_status=ModerationStatus.APPROVED)),
            rejected=Count('id', filter=Q(moderation_status=ModerationStatus.REJECTED)),
            flagged=Count('id', filter=Q(moderation_status=ModerationStatus.FLAGGED)),
            deleted=Count('id', filter=Q(is_deleted=True)),
        )

        self.stdout.write(self.style.SUCCESS('\n=== Project Moderation Statistics ==='))
        self.stdout.write(f'Total Projects: {stats["total"]}')
        self.stdout.write(f'Pending Review: {stats["pending"]}')
        self.stdout.write(f'Approved: {stats["approved"]}')
        self.stdout.write(f'Rejected: {stats["rejected"]}')
        self.stdout.write(f'Flagged: {stats["flagged"]}')
        self.stdout.write(f'Deleted: {stats["deleted"]}')

    def cleanup_deleted(self, options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_projects = Project.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )

        count = deleted_projects.count()

        if count == 0:
            self.stdout.write(self.style.WARNING('No old deleted projects found'))
            return

        self.stdout.write(
            self.style.WARNING(
                f'Found {count} projects deleted more than {days} days ago'
            )
        )

        confirm = input('Permanently delete these projects? [y/N]: ')
        if confirm.lower() != 'y':
            self.stdout.write('Cancelled')
            return

        deleted_projects.delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} projects'))

    def _get_admin(self, email):
        if email:
            try:
                return User.objects.get(email=email, is_staff=True)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Admin {email} not found, using system admin')
                )

        admin, created = User.objects.get_or_create(
            username='system_moderator',
            defaults={
                'email': 'moderator@system.local',
                'is_staff': True,
                'is_active': True,
            }
        )
        return admin
