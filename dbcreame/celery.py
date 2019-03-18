from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import worker_init, celeryd_init

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dbcreame.settings')

app = Celery('dbcreame')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Priorities configuration
app.conf.task_queue_max_priority = 10

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@app.task(name='celery.ping')
def ping():
    # type: () -> str
    """Simple task that just returns 'pong'."""
    return 'pong'

@worker_init.connect
def limit_chord_unlock_tasks(sender, **kwargs):
    """
    Set max_retries for chord.unlock tasks to avoid infinitely looping
    tasks. (see celery/celery#1700 or celery/celery#2725)
    """
    print("Worker configured")
    task = sender.app.tasks['celery.chord_unlock']
    if task.max_retries is None:
        retries = getattr(worker.app.conf, 'CHORD_UNLOCK_MAX_RETRIES', None)
        task.max_retries = retries
