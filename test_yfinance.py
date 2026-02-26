import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/vintex/Documents/work/cot-back')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from datahandler.scraper.Seasonality import MarketDataHandler

def test_yfinance_optimization():
    handler = MarketDataHandler()
    
    # Test with a few symbols
    test_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    print("🚀 Starting optimized yfinance test...")
    for symbol in test_symbols:
        try:
            print(f"\n--- Testing {symbol} ---")
            df = handler.fetch_yahoo_data(symbol)
            if not df.empty:
                print(f"✅ Success! Fetched {len(df)} rows for {symbol}")
                print(f"Last 5 rows:\n{df.tail()}")
            else:
                print(f"❌ Failed to fetch data for {symbol} (empty DataFrame)")
        except Exception as e:
            print(f"❌ Exception for {symbol}: {e}")

if __name__ == "__main__":
    test_yfinance_optimization()
