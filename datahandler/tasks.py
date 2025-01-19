from celery import shared_task
from .handler import execute
from .calendar_handler import main
from .scraper.Seasonality import MarketDataHandler


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

@shared_task
def fetch_seasonality():
    print("Updating seasonality")
    h = MarketDataHandler()
    h.execute()
