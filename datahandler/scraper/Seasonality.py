import requests
from ..utils import get_proxies

import pandas as pd
from datetime import datetime, timedelta
from datahandler.models import Symbol,Seasonality,Trends
import time
import random
import pandas as pd
import traceback
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

symbol_id_list = {'AUDCAD': '8',
 'AUDJPY': '9',
 'AUDNZD': '10',
 'AUDUSD': '11',
 'CADJPY': '12',
 'EURAUD': '6',
 'EURCAD': '13',
 'EURCHF': '14',
 'EURCZK': '15',
 'EURGBP': '17',
 'EURJPY': '7',
 'EURUSD': '1',
 'GBPJPY': '4',
 'GBPUSD': '2',
 'NZDUSD': '28',
 'USDCAD': '5',
 'USDCHF': '29',
 'USDJPY': '3',
 'XAGUSD': '50',
 'XAUUSD': '51',
 'AUDCHF': '47',
 'CADCHF': '103',
 'CHFJPY': '46',
 'NZDJPY': '27',
 'NZDCHF': '49',
 'GBPNZD': '48',
 'EURNZD': '20',
 'GBPCAD': '24',
 'GBPCHF': '25',
 'NZDCAD': '26',
 'GBPAUD': '107'}




class MarketDataHandler:
    """
    A class to handle fetching and analyzing market data for multiple symbols.
    """
    
    BASE_URL = "https://www.myfxbook.com/tvc/history"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.myfxbook.com/",
        "Origin": "https://www.myfxbook.com",
        "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    def __init__(self):
        """
        Initialize the MarketDataHandler with a dictionary of symbols and their IDs.

        Args:
            symbol_id_list (dict): Dictionary of symbol names and their corresponding IDs.
        """
        self.symbol_id_list = symbol_id_list

    

    @staticmethod
    def calculate_percentage_change(data, period):
        """
        Calculate the percentage change for the given period.

        Args:
            data (pd.Series): A series of closing prices.
            period (int): Number of periods for calculating % change.
        
        Returns:
            pd.Series: Percentage change series.
        """
        return data.pct_change(periods=period) * 100

    def fetch_data(self, symbol_id, resolution, from_timestamp, to_timestamp):
        """
        Fetch historical data for a specific symbol.

        Args:
            symbol_id (str): Symbol ID to fetch data for.
            resolution (str): Data resolution ('1M' for monthly, '1W' for weekly, etc.).
            from_timestamp (int): Start timestamp for fetching data.
            to_timestamp (int): End timestamp for fetching data.

        Returns:
            pd.DataFrame: A DataFrame containing the historical data.
        """
        url = f"{self.BASE_URL}?symbol={symbol_id}&resolution={resolution}&from={from_timestamp}&to={to_timestamp}"
        response = requests.get(url, headers=self.HEADERS, proxies=get_proxies())

        response.raise_for_status()
        data = response.json()

        if not all(key in data for key in ["t", "o", "h", "c", "l"]):
            raise ValueError("The response data does not contain the expected keys.")

        df = pd.DataFrame(data)
        df["human_readable_time"] = pd.to_datetime(df["t"], unit="s")
        return df.sort_values(by="t", ascending=True).reset_index(drop=True)

    def add_weekly_trend_columns(self, df):
        """
        Adds 'weekly_trend' (1-week % change) and 'rolling_3w_trend' (sum of last 3 weeks' % change)
        columns to the weekly data DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing weekly data with 'c' column for close prices.

        Returns:
            pd.DataFrame: DataFrame with added columns.
        """
        df = df.copy()
        df["weekly_trend"] = self.calculate_percentage_change(df["c"], 1)
        df["rolling_3w_trend"] = df["weekly_trend"].rolling(window=3).sum().shift(1)
        return df

    def calculate_seasonality(self, df,year):
        """
        Calculate seasonality based on the last 5 full years of data for each month.

        Args:
            df (pd.DataFrame): DataFrame containing monthly data.

        Returns:
            pd.Series: Monthly seasonality as a percentage.
        """
        # Calculate percentage change
        df["monthly_change"] = self.calculate_percentage_change(df["c"], 1)

        # Extract the year and month for filtering
        df["year"] = df["human_readable_time"].dt.year
        df["month"] = df["human_readable_time"].dt.month

        # Get the current year and month
        current_year = year
        current_month = datetime.now().month

        # Filter data to include only the last 5 full years (excluding the current year)
        filtered_data = pd.DataFrame()
        for month in range(1, 13):  # Loop through months (1 to 12)
            # Include data for the last 5 full years (excluding current year)
            month_data = df[
                (df["month"] == month) & (df["year"] >= current_year - 5) & (df["year"] < current_year)
            ]
            filtered_data = pd.concat([filtered_data, month_data])

        # Group by month and calculate the average of monthly changes
        seasonality = filtered_data.groupby("month")["monthly_change"].mean()

        return seasonality

    def calculate_trend(self, df,year):
        """
        Calculate the trend based on the 3 weeks prior to the last week of data.

        Args:
            df (pd.DataFrame): DataFrame containing weekly data.

        Returns:
            float: Trend as a sum of the % change over the specified weeks.
        """
        # Calculate weekly percentage change
        df["weekly_change"] = self.calculate_percentage_change(df["c"], 1)
        
        # Exclude the last week
        if len(df) < 4:
            # Not enough data to calculate the trend
            return 0.0

        # Sum the percentage change for the three weeks prior to the last week
        return df["weekly_change"].iloc[-4:-1].sum()
    
    
    
    def analyze_trend(self,symbol_id,from_timestamp,to_timestamp,year,symbol):
        # Fetch weekly data
        weekly_data = self.fetch_data(symbol_id, "1W", from_timestamp, to_timestamp)
        weekly_data = self.add_weekly_trend_columns(weekly_data)
        trend = self.calculate_trend(weekly_data,year)

        # Get or create the symbol instance
        symbol_instance, _ = Symbol.objects.get_or_create(name=symbol)

        # Save the weekly trend data
        #self.save_weekly_trends(symbol_instance, weekly_data)
        return trend

    def analyze_symbol(self, symbol, symbol_id,year):
        """
        Analyze a single symbol to calculate seasonality and trend.

        Args:
            symbol (str): Symbol name.
            symbol_id (str): Symbol ID.

        Returns:
            dict: A dictionary containing seasonality and trend for the symbol.
        """
        # Adjust the from_timestamp to fetch 6 years of data
        to_timestamp = int(datetime.now().timestamp())
        from_timestamp = int((datetime.now() - timedelta(days=15 * 365)).timestamp())

        # Fetch monthly data
        monthly_data = self.fetch_data(symbol_id, "1M", from_timestamp, to_timestamp)
        seasonality = self.calculate_seasonality(monthly_data,year)
        trend = self.analyze_trend(symbol_id,from_timestamp,to_timestamp,year,symbol)
        

        return {
            "symbol": symbol,
            "seasonality": seasonality,
            "trend": trend,
        }

    def analyze_all_symbols(self,start_year):
        """
        Analyze all symbols in the symbol_id_list.

        Returns:
            dict: A dictionary containing analysis results for all symbols.
        """
        final_res = {}
        for year in range(start_year,datetime.now().year + 1):
            results = {}
            for symbol, symbol_id in self.symbol_id_list.items():
                try:
                    results[symbol] = self.analyze_symbol(symbol, symbol_id,year)
                    print(f"Analysis completed for {symbol}.")
                except Exception as e:
                    print(f"Failed to analyze {symbol}: {e}")
            final_res[year] = results
        return final_res
    

    def fetch_yahoo_data(self, symbol, interval='1d', start="2010-01-01", end=None, max_retries=3):
        """
        Directly fetches data from the Yahoo Finance API using curl_cffi for browser impersonation.
        Bypasses the unstable yfinance library.
        """
        symbol_yahoo = symbol + "=X"
        print(f"Fetching data for {symbol_yahoo} via direct Yahoo API...")
        
        # Convert dates to timestamps
        try:
            start_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
            if end:
                end_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp())
            else:
                end_ts = int(time.time())
        except Exception as e:
            print(f"❌ Date conversion error: {e}")
            return pd.DataFrame()

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_yahoo}"
        params = {
            "period1": start_ts,
            "period2": end_ts,
            "interval": interval,
            "events": "div|split",
            "includePrePost": "false"
        }

        for attempt in range(max_retries):
            try:
                # Use a unique 8-char session ID for proxy sticky sessions
                session_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                proxies = get_proxies(session_id=session_id)
                
                if curl_requests:
                    response = curl_requests.get(
                        url, 
                        params=params, 
                        proxies=proxies, 
                        impersonate="chrome", 
                        timeout=30 # Increased timeout for residential proxies
                    )
                else:
                    response = requests.get(
                        url, 
                        params=params, 
                        proxies=proxies, 
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=30
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    if "chart" in data and data["chart"]["result"]:
                        result = data["chart"]["result"][0]
                        timestamps = result.get("timestamp", [])
                        indicators = result.get("indicators", {}).get("quote", [{}])[0]
                        closes = indicators.get("close", [])
                        
                        if not timestamps or not closes:
                            print(f"⚠️ Received empty data components for {symbol_yahoo} (Attempt {attempt+1}/{max_retries})")
                            time.sleep(random.uniform(2, 5))
                            continue
                        
                        df = pd.DataFrame({
                            'datetime': [datetime.fromtimestamp(ts) for ts in timestamps],
                            'c': closes,
                            't': timestamps
                        })
                        
                        # Clean NaN values
                        df = df.dropna(subset=['c'])
                        
                        if df.empty:
                            print(f"⚠️ Resulting DataFrame is empty after cleaning for {symbol_yahoo}")
                            continue
                            
                        print(f"✅ Successfully fetched {len(df)} rows for {symbol_yahoo}")
                        return df
                    else:
                        print(f"⚠️ Unexpected JSON structure for {symbol_yahoo}: {data}")
                elif response.status_code == 429:
                    print(f"🚦 Rate limited for {symbol_yahoo} (Attempt {attempt+1}/{max_retries})")
                else:
                    print(f"❌ Error response {response.status_code} for {symbol_yahoo}: {response.text[:200]}")
                
            except Exception as e:
                print(f"❌ Exception fetching {symbol_yahoo} (Attempt {attempt+1}/{max_retries}): {e}")
                # Log full traceback to help debug server-side failures
                traceback.print_exc()
            
            # Backoff
            sleep_time = random.uniform(3, 7) * (attempt + 1)
            print(f"Sleeping {sleep_time:.2f}s before retry...")
            time.sleep(sleep_time)
                
        print(f"🛑 Failed to fetch data for {symbol_yahoo} after {max_retries} attempts.")
        return pd.DataFrame()

    def calculate_new_trend(self, df):
        df = df.copy()
        df['trend'] = (df['c'] - df['c'].shift(15)) / df['c'].shift(15) * 100  # percent change
        df['user_trend'] = (df['c'] - df['c'].shift(21)) / df['c'].shift(21) * 100
        return df
    
    def calculate_user_trend(self, df):
        """
        Calculate user_trend as ((current close - close 3 weeks ago) / close 3 weeks ago) * 100
        Assuming 1 day = 1 row, so 3 weeks = 21 trading days.
        """
        df = df.copy()
        df['user_trend'] = (df['c'] - df['c'].shift(21)) / df['c'].shift(21) * 100
        return df

    def update_trends(self):
        for symbol, symbol_id in self.symbol_id_list.items():
            try:
                df = self.fetch_yahoo_data(symbol)
                df = self.calculate_new_trend(df)
                self.save_trends(symbol, df)
                print(f"Trends updated for {symbol}")
            except Exception as e:
                print(f"Error processing {symbol}: {e}")

    def save_trends(self, symbol, df):
        symbol_instance = Symbol.objects.get(name=symbol)
        for _, row in df.iterrows():
            if pd.isna(row['trend']):
                continue
            dt = row['datetime']
            t = int(row['t'])
            trend_value = row['trend']
            user_trend_value = row.get('user_trend', None)
            Trends.objects.update_or_create(
                symbol=symbol_instance,
                date=dt,
                defaults={
                    'change': trend_value,
                    'trend': trend_value,
                    'user_trend': user_trend_value
                }
            )

    def save_market_data(self,final_data):
        """
        Save or update market data into Django models.

        Args:
            data (dict): The market data dictionary.
            year (int): The year of the seasonality data.
        """
        for year in final_data.keys():
            data = final_data[year]
            for symbol_name, symbol_data in data.items():
                # Save or update the Symbol
                symbol, created = Symbol.objects.update_or_create(
                    name=symbol_name,
                    defaults={'trend': symbol_data['trend']}
                )

                # Save or update Seasonality for the year
                seasonality_data = symbol_data['seasonality']
                for month, value in seasonality_data.items():
                    Seasonality.objects.update_or_create(
                        symbol=symbol,
                        year=year,
                        month=month,
                        defaults={'value': value}
                    )
    
    def execute(self):
        res = self.analyze_all_symbols(2020)
        self.save_market_data(res)