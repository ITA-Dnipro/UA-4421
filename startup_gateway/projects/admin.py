from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from projects.models import (
    Project,
    ProjectModerationLog,
    ProjectModerationStats,
    Tag, ModerationAction
)
from projects.services.moderation_service import ProjectModerationService


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'startup_name', 'moderation_status_badge',
        'is_deleted', 'created_at', 'moderated_by_name'
    ]
    list_filter = [
        'moderation_status', 'is_deleted', 'status', 'visibility', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'startup_profile__company_name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'moderated_at', 'deleted_at'
    ]
    actions = ['approve_projects', 'flag_projects']

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'startup_profile', 'short_description', 'description')
        }),
        ('Status', {
            'fields': ('status', 'visibility', 'moderation_status')
        }),
        ('Moderation', {
            'fields': (
                'moderation_notes', 'rejection_reason',
                'moderated_by', 'moderated_at'
            )
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_by', 'deleted_at'),
            'classes': ('collapse',)
        }),
        ('Financial', {
            'fields': ('target_amount', 'raised_amount')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def startup_name(self, obj):
        return obj.startup_profile.company_name

    startup_name.short_description = 'Startup'
    startup_name.admin_order_field = 'startup_profile__company_name'

    def moderation_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'flagged': 'purple'
        }
        color = colors.get(obj.moderation_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.moderation_status.upper()
        )

    moderation_status_badge.short_description = 'Moderation'

    def moderated_by_name(self, obj):
        if obj.moderated_by:
            return obj.moderated_by.username
        return '-'

    moderated_by_name.short_description = 'Moderated By'

    def approve_projects(self, request, queryset):

        count = 0
        for project in queryset:
            success, _, _ = ProjectModerationService.moderate_project(
                project=project,
                action=ModerationAction.APPROVE,
                moderator=request.user,
                notes='Bulk approved via admin'
            )
            if success:
                count += 1

        self.message_user(request, f'Successfully approved {count} project(s)')

    approve_projects.short_description = 'Approve selected projects'

    def flag_projects(self, request, queryset):

        count = 0
        for project in queryset:
            success, _, _ = ProjectModerationService.moderate_project(
                project=project,
                action=ModerationAction.FLAG,
                moderator=request.user,
                reason='Flagged via admin',
                notes='Manual flag'
            )
            if success:
                count += 1

        self.message_user(request, f'Successfully flagged {count} project(s)')

    flag_projects.short_description = 'Flag selected projects'


@admin.register(ProjectModerationLog)
class ProjectModerationLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project_title', 'action', 'moderator_name',
        'old_status', 'new_status', 'created_at'
    ]
    list_filter = ['action', 'created_at']
    search_fields = ['project__title', 'moderator__username', 'reason']
    readonly_fields = ['created_at']

    def project_title(self, obj):
        return obj.project.title

    project_title.short_description = 'Project'

    def moderator_name(self, obj):
        if obj.moderator:
            return obj.moderator.username
        return 'System'

    moderator_name.short_description = 'Moderator'


@admin.register(ProjectModerationStats)
class ProjectModerationStatsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'pending_count', 'approved_count', 'rejected_count',
        'flagged_count', 'deleted_count', 'restored_count'
    ]
    list_filter = ['date']
    readonly_fields = [
        'date', 'pending_count', 'approved_count', 'rejected_count',
        'flagged_count', 'deleted_count', 'restored_count'
    ]
