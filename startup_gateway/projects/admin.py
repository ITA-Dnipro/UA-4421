from django.contrib import admin
from django.utils.html import format_html
from .models import Project, ProjectModerationLog

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'startup_name', 'moderation_status_badge', 'created_at']
    list_filter = ['moderation_status', 'is_deleted', 'created_at']
    search_fields = ['title', 'startup_profile__company_name']
    readonly_fields = ['created_at', 'updated_at', 'moderated_at']

    def startup_name(self, obj):
        return obj.startup_profile.company_name
    startup_name.short_description = 'Startup'

    def moderation_status_badge(self, obj):
        colors = {'pending': 'orange', 'approved': 'green', 'rejected': 'red', 'flagged': 'purple'}
        color = colors.get(obj.moderation_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.moderation_status.upper()
        )
    moderation_status_badge.short_description = 'Status'


@admin.register(ProjectModerationLog)
class ProjectModerationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'project_title', 'action', 'moderator_name', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['project__title', 'moderator__username']
    readonly_fields = ['created_at']

    def project_title(self, obj):
        return obj.project.title
    project_title.short_description = 'Project'

    def moderator_name(self, obj):
        return obj.moderator.username if obj.moderator else 'System'
    moderator_name.short_description = 'Moderator'
