from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
import datetime

# 这里我们的项目名称为xiaopgg_project,所以为xiaopgg_project.settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xiaopgg_project.settings")

# 创建celery应用
app = Celery('celery_app')


def custom_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)


app.now = custom_now
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
