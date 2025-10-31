from celery import shared_task
from .handler import execute
from .calendar_handler import main
from .scraper.Seasonality import MarketDataHandler
from .scraper.Sentiment import Sentiment


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

@shared_task
def fetch_trends():
    print("Updating Trends")
    h = MarketDataHandler()
    h.update_trends()


@shared_task(name="datahandler.tasks.manual_fetch_data")
def manual_fetch_data():
    print("Manual: fetching the data")
    execute()


@shared_task(name="datahandler.tasks.manual_fetch_calendar")
def manual_fetch_calendar():
    print("Manual: fetching calendar data")
    main()


@shared_task(name="datahandler.tasks.manual_fetch_seasonality")
def manual_fetch_seasonality():
    print("Manual: Updating seasonality")
    h = MarketDataHandler()
    h.execute()


@shared_task(name="datahandler.tasks.manual_fetch_trends")
def manual_fetch_trends():
    print("Manual: Updating trends")
    h = MarketDataHandler()
    h.update_trends()


@shared_task
def fetch_sentiment():
    print("Fetching MyFXBook sentiment data...")
    s = Sentiment()
    s.execute()