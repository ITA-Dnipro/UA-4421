import json

from django.contrib import admin
from django.db import models
from django.forms import Textarea

from .models import LandingContent


class PrettyJSONWidget(Textarea):
    def format_value(self, value):
        if value in (None, ""):
            return ""

        try:
            if isinstance(value, str):
                value = json.loads(value)

            return json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return super().format_value(value)


@admin.register(LandingContent)
class LandingContentAdmin(admin.ModelAdmin):
    list_display = ("id", "updated_at")
    readonly_fields = ("updated_at",)

    formfield_overrides = {
        models.JSONField: {
            "widget": PrettyJSONWidget(
                attrs={
                    "rows": 20,
                    "cols": 100,
                    "style": "font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;",
                    "spellcheck": "false",
                }
            )
        }
    }
