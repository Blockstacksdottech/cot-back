import requests
import pandas as pd
from datetime import datetime, timedelta
from datahandler.models import Symbol,Seasonality

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
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if not all(key in data for key in ["t", "o", "h", "c", "l"]):
            raise ValueError("The response data does not contain the expected keys.")

        df = pd.DataFrame(data)
        df["human_readable_time"] = pd.to_datetime(df["t"], unit="s")
        return df.sort_values(by="t", ascending=True).reset_index(drop=True)

    def calculate_seasonality(self, df):
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
        current_year = datetime.now().year
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

    def calculate_trend(self, df):
        """
        Calculate the trend based on the last 3 weeks of data.

        Args:
            df (pd.DataFrame): DataFrame containing weekly data.

        Returns:
            float: Trend as a sum of the % change over the last 3 weeks.
        """
        df["weekly_change"] = self.calculate_percentage_change(df["c"], 1)
        return df["weekly_change"].iloc[-3:].sum()

    def analyze_symbol(self, symbol, symbol_id):
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
        from_timestamp = int((datetime.now() - timedelta(days=6 * 365)).timestamp())

        # Fetch monthly data
        monthly_data = self.fetch_data(symbol_id, "1M", from_timestamp, to_timestamp)
        seasonality = self.calculate_seasonality(monthly_data)

        # Fetch weekly data
        weekly_data = self.fetch_data(symbol_id, "1W", from_timestamp, to_timestamp)
        trend = self.calculate_trend(weekly_data)

        return {
            "symbol": symbol,
            "seasonality": seasonality,
            "trend": trend,
        }

    def analyze_all_symbols(self):
        """
        Analyze all symbols in the symbol_id_list.

        Returns:
            dict: A dictionary containing analysis results for all symbols.
        """
        results = {}
        for symbol, symbol_id in self.symbol_id_list.items():
            try:
                results[symbol] = self.analyze_symbol(symbol, symbol_id)
                print(f"Analysis completed for {symbol}.")
            except Exception as e:
                print(f"Failed to analyze {symbol}: {e}")
        return results
    
    def save_market_data(self,data, year):
        """
        Save or update market data into Django models.

        Args:
            data (dict): The market data dictionary.
            year (int): The year of the seasonality data.
        """
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
        res = self.analyze_all_symbols()
        self.save_market_data(res,datetime.now().year)