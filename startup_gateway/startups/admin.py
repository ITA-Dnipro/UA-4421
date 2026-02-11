from django.contrib import admin
from .models import StartupProfile

@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'company_name', 'slug', 'website', 'created_at')
    search_fields = ('company_name', 'slug', 'website')
    list_filter = ('created_at',)
