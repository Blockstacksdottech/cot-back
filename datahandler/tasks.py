from celery import shared_task
from .handler import execute
from .calendar_handler import main


@shared_task
def test():
    print("This is a test task")


@shared_task
def fetch_data():
    print("fetching the data")
    execute()

@shared_task
def fetch_calendar():
    print("fetching calendar data")
    main()
