import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "startup_gateway.settings")

app = Celery("startup_gateway")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
