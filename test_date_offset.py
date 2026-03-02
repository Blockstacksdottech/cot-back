import os
import django
import sys
from datetime import datetime, timezone
import pandas as pd

# Setup Django environment
sys.path.append('/Users/vintex/Documents/work/cot-back')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from datahandler.scraper.Seasonality import MarketDataHandler

def test_date_fetching():
    handler = MarketDataHandler()
    symbol = "EURUSD"
    
    # Test case: Fetch data for a recent window
    test_start = "2026-02-20"
    test_end = "2026-02-27" # Using 27 because today is 28th and 28th might not be closed yet
    
    print(f"🚀 Fetching {symbol} data from {test_start} to {test_end}")
    
    # Run the fetcher
    df = handler.fetch_yahoo_data(symbol, start=test_start, end=test_end)
    
    if not df.empty:
        print("\nFetched Data Summary:")
        print(df.tail(5))
        
        last_date = df.iloc[-1]['datetime']
        print(f"\nLast available date in DF: {last_date}")
        
        # Parse comparison date as UTC
        expected_end = datetime.strptime(test_end, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
        
        if last_date.date() < expected_end:
            print(f"❌ BUG PERSISTS: Requested up to {test_end}, but last date is {last_date.date()}")
        elif last_date.date() == expected_end:
            print(f"✅ SUCCESS: Requested date {test_end} is included in data.")
        else:
            print(f"✅ Requested date included (Data goes up to {last_date.date()}).")
    else:
        print("❌ Received empty DataFrame.")

if __name__ == "__main__":
    test_date_fetching()
