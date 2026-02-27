from django.core.management.base import BaseCommand
from datahandler.scraper.Seasonality import MarketDataHandler
from datahandler.scraper.Sentiment import Sentiment
from datahandler.handler import execute as fetch_cot_data
from datahandler.calendar_handler import main as fetch_calendar_data

class Command(BaseCommand):
    help = 'Manually trigger market data updates (Seasonality, Trends, Sentiment, COT, Calendar)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            help='What to update: trends, seasonality, sentiment, cot, calendar, or all',
        )

    def handle(self, *args, **options):
        update_type = options['type'].lower()
        
        handler = MarketDataHandler()
        
        if update_type in ['trends', 'all']:
            self.stdout.write(self.style.SUCCESS('🚀 Starting Trends update...'))
            handler.update_trends()
            self.stdout.write(self.style.SUCCESS('✅ Trends update completed.'))

        if update_type in ['seasonality', 'all']:
            self.stdout.write(self.style.SUCCESS('🚀 Starting Seasonality update...'))
            handler.execute()
            self.stdout.write(self.style.SUCCESS('✅ Seasonality update completed.'))

        if update_type in ['sentiment', 'all']:
            self.stdout.write(self.style.SUCCESS('🚀 Starting Sentiment update...'))
            s = Sentiment()
            s.execute()
            self.stdout.write(self.style.SUCCESS('✅ Sentiment update completed.'))

        if update_type in ['cot', 'all']:
            self.stdout.write(self.style.SUCCESS('🚀 Starting COT data fetch...'))
            fetch_cot_data()
            self.stdout.write(self.style.SUCCESS('✅ COT data fetch completed.'))

        if update_type in ['calendar', 'all']:
            self.stdout.write(self.style.SUCCESS('🚀 Starting Calendar data fetch...'))
            fetch_calendar_data()
            self.stdout.write(self.style.SUCCESS('✅ Calendar data fetch completed.'))
