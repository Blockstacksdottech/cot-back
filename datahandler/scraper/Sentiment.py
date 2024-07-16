import requests
from bs4 import BeautifulSoup


class Sentiment:
    def __init__(self):
        # Replace with the actual website URL
        self.url = 'https://www.myfxbook.com/community/outlook'
        self.symbol_list = ['AUD/JPY',
                            'EUR/AUD',
                            'AUD/CHF',
                            'CAD/CHF',
                            'CHF/JPY',
                            'EUR/JPY',
                            'EUR/CHF',
                            'AUD/CAD',
                            'EUR/CAD',
                            'CAD/JPY',
                            'AUD/NZD',
                            'NZD/JPY',
                            'NZD/CHF',
                            'GBP/NZD',
                            'EUR/NZD',
                            'USD/JPY',
                            'AUD/USD',
                            'GBP/CAD',
                            'GBP/CHF',
                            'GBP/JPY',
                            'NZD/CAD',
                            'USD/CAD',
                            'GBP/AUD',
                            'EUR/GBP',
                            'GBP/USD',
                            'USD/CHF',
                            'EUR/USD',
                            'NZD/USD']

    def extract_symbol_data(self, element):
        """Extracts symbol data (short/long positions, percentage, volume) from the given HTML.

        Args:
            html_content (str): The HTML content containing the symbol data.

        Returns:
            dict: A dictionary containing the extracted data, or None if no data found.
        """

        # Find the table element with the specified classes
        table = element.find('tbody')

        if not table:
            print("Table element not found in the provided HTML.")
            return None

        symbol_data = {}
        symbol = table.find('td', rowspan="2").text.strip()
        symbol_data[symbol] = {}  # Assuming 'Symbol' is in the first <th>

        # Extract data from each table row (<tr>)
        for row in table.find_all('tr'):
            # print(row)
            action = row.find('td', text=lambda text: text and text.strip().lower() in [
                              "short", "long"]).text.strip()  # Skip header row
            percentage = row.find(
                'td', text=lambda text: '%' in text).text.strip()
            volume = row.find(
                'td', text=lambda text: 'lots' in text).text.strip()
            positions = row.find_all('td')[-1].text.strip()

            if action:  # Skip header row
                symbol_data[symbol][action] = {
                    'percentage': percentage,
                    'volume': volume,
                    'positions': positions
                }

        # Extract overall trader percentage (optional)
        trader_percentage_element = element.find(
            class_='text-center margin-top-5')
        if trader_percentage_element:
            symbol_data['traders_percentage'] = trader_percentage_element.text.strip()

        return symbol_data

    def get_outlook_data(self, url, symbol_list):
        """Fetches outlook data for specified symbols from the given website.

        Args:
            url (str): The URL of the website to scrape.
            symbol_list (list): A list of currency pairs (e.g., ['AUDCAD', 'EURJPY']).

        Returns:
            list: A list of dictionaries containing symbol and outlook data (if found).
        """

        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Filter symbol list to remove duplicates and ensure uppercase for consistency
        unique_symbols = list(
            set([symbol.upper().replace('/', '') for symbol in symbol_list]))

        outlook_data = []
        for symbol in unique_symbols:
            # Construct the expected ID pattern for the outlook popover element

            # Find all table rows (<tr>) containing the symbol name
            symbol_rows = soup.find_all(
                'tr', symbolname=lambda text: text and symbol in text.upper())

            for row in symbol_rows:
                # Extract the symbol ID attribute from the table row
                symbolid = row.get('symbolid')
                outlook_id_pattern = f"outlookSymbolPopover{symbolid}"

                # Check if the corresponding outlook popover element exists
                outlook_element = soup.find(id=outlook_id_pattern)

                if outlook_element:
                    outlook_data.append(
                        self.extract_symbol_data(outlook_element))
                else:
                    print(f"Outlook popover not found for symbol: {symbol}")

        return outlook_data

    def execute(self):
        outlook_data = self.get_outlook_data(self.url, self.symbol_list)

        return outlook_data

    def scrape_adr(self):
        pass
