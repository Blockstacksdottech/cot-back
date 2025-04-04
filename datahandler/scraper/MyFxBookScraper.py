import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
from datetime import datetime,timedelta
import  time


  
class MyFXBookScraper:
    BASE_URL = "https://widget.myfxbook.com/calendar/search.html"
    HEADERS = {
        "authority": "widget.myfxbook.com",
        "content-type": "application/json"
    }

    def __init__(self, start_date, end_date=None, currencies=None):
        self.start_date = datetime.strptime(start_date, "%d-%m-%Y")
        self.end_date = datetime.strptime(end_date, "%d-%m-%Y") if end_date else datetime.today()
        self.currencies = currencies or ["USD", "JPY"]  # Default to USD and JPY
        self.data = []

    def fetch_data(self):
        """Fetch data from MyFXBook API in weekly intervals."""
        current_date = self.start_date

        while current_date <= self.end_date:
            # Calculate the end date of this week (7 days after the current date)
            end_date = current_date + timedelta(days=6)

            # Ensure the end date does not exceed the overall end date
            if end_date > self.end_date:
                end_date = self.end_date

            print(f"Fetching data for the period: {current_date} => {end_date}")

            payload = {
                "startDate": current_date.strftime("%Y-%m-%dT00:00:00.000Z"),  # Start date
                "endDate": end_date.strftime("%Y-%m-%dT23:59:59.999Z"),  # End date
                "language": "en",
                "impacts": ["3", "2","1","0"],  # High & Medium impact events
                "currencies": self.currencies
            }
            try:
                res = requests.post(self.BASE_URL, json=payload, headers=self.HEADERS)
                if res.status_code == 200:
                    html_content = res.content.decode()

                    # Save the response to an HTML file with the format: start_end.html
                    file_name = f"{current_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.html"
                    #with open(file_name, "w", encoding="utf-8") as file:
                    #    file.write(html_content)
                    #print(f"Saved response to {file_name}")

                    # Optionally, parse the HTML into a DataFrame if needed
                    df = self.parse_html(html_content)
                    self.data.extend(df.to_dict(orient="records"))
                    # Move to the next week (7 days ahead)
                    current_date = end_date + timedelta(days=1)
                else:
                    print(f"Failed to fetch data for {current_date.strftime('%Y-%m-%d')}")
                    time.sleep(5)
            except Exception as e:
                time.sleep(5)
                continue

        return pd.DataFrame(self.data)
    
    def filter_with_event(self,df, query, currency):
        """
        Filters the DataFrame based on event category and currency.

        :param df: Pandas DataFrame containing MyFXBook event data.
        :param query: The category to filter by (e.g., "gdp", "cpi", "employment").
        :param currency: The currency code to filter by (e.g., "USD", "EUR").
        :return: Filtered DataFrame containing only matching events.
        """
        if query not in EVENT_PATTERNS:
            raise ValueError(f"Invalid event category: {query}")

        # Get the regex pattern for the given currency & query
        options = EVENT_PATTERNS[query]
        regex_pattern = options.get(currency, options.get("all", None))

        if not regex_pattern:
            return df.iloc[0:0]  # Return an empty DataFrame if no match found

        # Filter the dataset by currency
        filtered_df = df[df['Currency'] == currency]

        # Filter by importance level
        filtered_df = filtered_df[filtered_df['Impact'].isin(['low', 'medium', 'high'])]

        # Filter by event name using regex
        filtered_df = filtered_df[filtered_df['Event'].str.contains(regex_pattern, case=False, na=False)]

        return filtered_df

    @staticmethod
    def convert_value(value):
        """Convert values with K, M, B to full numbers and keep percentages unchanged."""
        if not value or value == '-':
            return None  # Handle empty values

        value = value.replace(',', '')  # Remove commas
        match = re.match(r'([\d\.]+)([KMB%]*)', value)  # Extract number and suffix

        if not match:
            return value  # Return as is if no match

        num, suffix = match.groups()
        num = float(num)

        if suffix == 'K':
            num *= 1_000
        elif suffix == 'M':
            num *= 1_000_000
        elif suffix == 'B':
            num *= 1_000_000_000
        elif '%' in suffix:
            return f"{num}%"

        return int(num) if num.is_integer() else num

    @staticmethod
    def parse_html(html_content):
        """Parse the HTML response and extract structured data."""
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr', attrs={'data-calendar-row': True})

        data = []
        for row in rows:
            date_td = row.find('td', attrs={'data-event-date': True})
            date = pd.to_datetime(int(date_td['data-event-date']), unit='ms').strftime('%Y-%m-%d %H:%M') if date_td else None

            currency_event_td = row.find_all('td')[2]
            if currency_event_td:
                currency_div = currency_event_td.find_all('div')[1]
                event_div = currency_event_td.find_all('div')[2]
                currency = currency_div.text.strip() if currency_div else None
                event = event_div.text.strip() if event_div else None
            else:
                currency = event = None

            impact_td = row.find_all('td')[3]
            impact = impact_td.text.strip() if impact_td else None

            values_tds = row.find_all('td')[4:7]
            act = MyFXBookScraper.convert_value(values_tds[0].text.strip()) if values_tds[0] else None
            cons = MyFXBookScraper.convert_value(values_tds[1].text.strip()) if values_tds[1] else None
            prev = MyFXBookScraper.convert_value(values_tds[2].text.strip()) if values_tds[2] else None

            data.append({
                'Date': date,
                'Currency': currency,
                'Event': event,
                'Impact': impact,
                'Actual': act,
                'Consensus': cons,
                'Previous': prev
            })

        return pd.DataFrame(data)


