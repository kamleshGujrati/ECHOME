from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ECHOME.settings")

app = Celery("ECHOME")

# read config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# auto-discover tasks inside all apps
app.autodiscover_tasks(['worker'])


