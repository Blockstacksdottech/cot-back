# cot-back

## Scheduling commands
### linux
celery -A api worker -l INFO
### windows
celery -A api worker -l INFO -P eventlet
celery -A api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler