from django.core.management.base import BaseCommand
from datahandler.calendar_handler import fetch_data, filter_data, calculate_score_with_weights, save_analyzed_data, target
from datahandler.scraper.Seasonality import MarketDataHandler

class Command(BaseCommand):
    help = 'Fetches full historical data starting from 2020'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting full historical data fetch (from 2020)...'))
        
        # 1. Fetch
        # Pass full_history=True to fetch from 2020
        combined = fetch_data(full_history=True)
        
        if combined.empty:
             self.stdout.write(self.style.WARNING('No data fetched properly.'))
             return

        # 2. Filter
        self.stdout.write(self.style.SUCCESS('Filtering data...'))
        res = filter_data(target, combined)
        
        # 3. Analyze
        analyzed_result = {}
        self.stdout.write(self.style.SUCCESS('Analyzing data...'))
        for curr in target:
            if curr in res:
                curr_data = res[curr]
                sorted_data = curr_data.sort_values('datetime')
                analyzed = calculate_score_with_weights(sorted_data)
                analyzed_result[curr] = analyzed
        
        # 4. Save
        self.stdout.write(self.style.SUCCESS('Saving to database...'))
        save_analyzed_data(analyzed_result)
        
        self.stdout.write(self.style.SUCCESS('Successfully completed full historical data fetch.'))

        # 5. Seasonality & Trends
        self.stdout.write(self.style.SUCCESS('Starting Seasonality & Trends fetch...'))
        try:
            handler = MarketDataHandler()
            self.stdout.write(self.style.SUCCESS('Fetching Seasonality (from 2020)...'))
            handler.execute() # Fetches 2020-Present seasonality
            
            self.stdout.write(self.style.SUCCESS('Fetching Trends...'))
            handler.update_trends()
            
            self.stdout.write(self.style.SUCCESS('Successfully completed Seasonality & Trends fetch.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching Seasonality/Trends: {e}'))

