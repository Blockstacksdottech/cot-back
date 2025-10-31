import os

from celery import Celery
from celery.schedules import crontab
from kombu import Queue




# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

app = Celery('api')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_queues = (
    Queue('default', routing_key='default'),
    Queue('admin', routing_key='admin'),
)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange_type = 'direct'
app.conf.task_default_routing_key = 'default'

app.conf.task_routes = {
    'datahandler.tasks.fetch_data': {'queue': 'default'},
    'datahandler.tasks.fetch_calendar': {'queue': 'default'},
    'datahandler.tasks.fetch_seasonality': {'queue': 'default'},
    'datahandler.tasks.fetch_trends': {'queue': 'default'},
    'datahandler.tasks.fetch-sentiment-every-10min': {'queue': 'default'},
    'datahandler.tasks.manual_*': {'queue': 'admin'},  # pattern for admin-triggered tasks
}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


app.conf.beat_schedule = {
    # Executes every Monday morning at 7:30 a.m.
    'test-print': {
        'task': 'datahandler.tasks.fetch_data',
        'schedule': crontab(hour=0, minute=0),
        'args': (),
    },
    'test-calendar': {
        'task': 'datahandler.tasks.fetch_calendar',
        'schedule': crontab(minute='*/45'),
        'args': (),
    },
    'seasonality-task': {
        'task': 'datahandler.tasks.fetch_seasonality',
        'schedule': crontab(hour=0, minute=0),
        'args': (),
    },
    'trends-task': {
        'task': 'datahandler.tasks.fetch_trends',
        'schedule': crontab(minute='*/15'),
        'args': (),
    },
    'fetch-sentiment-every-10min': {
        'task': 'datahandler.tasks.fetch_sentiment',
        'schedule': crontab(minute='*/10'),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
