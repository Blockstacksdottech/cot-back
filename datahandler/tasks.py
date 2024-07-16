from celery import shared_task
from .handler import execute


@shared_task
def test():
    print("This is a test task")


@shared_task
def fetch_data():
    print("fetching the data")
    execute()
