from .models import *
import investpy
import datetime
import re
import numpy as np
import pandas as pd
from .events_const import final_values,target,zone_mapping,weights
import time
from .scraper.MyFxBookScraper import MyFXBookScraperParallel

START_DATE = "01/01/2020"

def get_current_date():
  """Gets the current date in the format dd/mm/yyyy.

  Returns:
    A string representing the current date in the format dd/mm/yyyy.
  """

  today = datetime.date.today()
  return today.strftime('%d/%m/%Y')


def get_month_range(start_date, end_date):
  """Generates a list of the first day of each month between the given start and end dates.

  Args:
    start_date: A string representing the start date in the format dd/mm/yyyy.
    end_date: A string representing the end date in the format dd/mm/yyyy.

  Returns:
    A list of strings, each representing the first day of a month in the range, in the format dd/mm/yyyy.
  """

  # Convert start and end dates to datetime objects
  start_date = datetime.datetime.strptime(start_date, '%d/%m/%Y')
  end_date = datetime.datetime.strptime(end_date, '%d/%m/%Y')

  # Initialize a list to store the monthly dates
  month_range = []

  # Iterate through each month in the range
  while start_date <= end_date:
    # Add the first day of the current month to the list
    month_range.append(start_date.strftime('%d/%m/%Y'))

    # Increment the start date to the next month
    start_date = start_date + datetime.timedelta(days=31)
    start_date = start_date.replace(day=1)
  
  current_date = get_current_date()
  if current_date != month_range[-1]:
    month_range.append(current_date)

  return month_range

def combine_dataframes(dataframes):
  """Combines an array of DataFrames into a single DataFrame.

  Args:
    dataframes: An array of DataFrames to be combined.

  Returns:
    A single DataFrame containing the combined data.
  """

  if not dataframes:
    raise ValueError("Dataframes array cannot be empty.")

  # Check if all DataFrames have the same columns
  if not all(df.columns.equals(dataframes[0].columns) for df in dataframes[1:]):
    raise ValueError("DataFrames must have the same columns.")

  # Concatenate the DataFrames along the rows (axis=0)
  combined_df = pd.concat(dataframes, axis=0, ignore_index=True)

  return combined_df

def fetch_data():
    all_data = []

    for currency in target:
        print(f"\nFetching data for {currency}...")

        scraper = MyFXBookScraperParallel(start_date="01-01-2020", currencies=[currency],max_workers=10)
        df = scraper.fetch_data()

        if df.empty:
            print(f"No data found for {currency}")
        else:
            print(f"Fetched {len(df)} records for {currency}")
            all_data.append(df)
        print("waiting to reset timer")
        time.sleep(15)

    if not all_data:
        raise ValueError("No data fetched for any currency.")

    combined = pd.concat(all_data, ignore_index=True)
    return combined

# Function to extract numeric values using regex and replace None with 0
def extract_numeric(value):
  if value is None or value in ['None', 'N/A']:
    return 0  # Handle None or N/A values by replacing them with 0

  value = str(value).replace(',', '')  # Remove commas if present

  # Regex to extract numeric part, including negative sign
  match = re.search(r'(-?\d+\.?\d*)', value)
  if match:
    number = float(match.group(1))

    # Handle suffixes
    if 'K' in value:
      return number * 1000
    elif 'M' in value:
      return number * 1000000
    elif 'B' in value:
      return number * 1000000000
    elif '%' in value:
      return number / 100  # Convert percentage to decimal

    return number  # Return the extracted number as float

  return 0  # Return 0 if no number is found

def filter_with_event(df,query,t):
    options = final_values[query]
    if t in options.keys():
        q = options[t]
    else:
        q = options['all']
    test_data = df[df['currency'] == t]
    test_data = test_data[test_data['importance'].isin(['low','medium','high'])]
    filtered_df = test_data[test_data['event'].str.contains(q, case=False)]
    return filtered_df

def filter_data(target_currencies, combined_df):
    """Filters the DataFrame based on predefined event patterns and currencies.

    Args:
        target_currencies (list): List of currency codes to filter.
        combined_df (pd.DataFrame): The full scraped dataset.

    Returns:
        dict: Dictionary containing filtered data per currency.
    """
    all_results = {}

    for currency in target_currencies:
        temp_data = []

        for event_category, options in final_values.items():
            q = options.get(currency, options.get('all', ''))  # Get regex pattern

            # Filter DataFrame for the specific currency
            test_data = combined_df[combined_df['Currency'] == currency]

            # Filter for impact levels
            test_data = test_data[test_data['Impact'].isin(['low', 'med', 'high'])]

            # Apply regex filter to 'Event' column
            filtered_df = test_data[test_data['Event'].str.contains(q, case=False, regex=True, na=False)]

            # Convert 'Date' to datetime format
            filtered_df['datetime'] = pd.to_datetime(filtered_df['Date'], format='%Y-%m-%d %H:%M')

            # Assign event category
            filtered_df['ev'] = event_category

            # Sort by datetime
            filtered_df = filtered_df.sort_values(by='datetime')

            # Apply numeric extraction to actual, consensus, and previous values
            filtered_df['num_actual'] = filtered_df['Actual'].apply(extract_numeric)
            filtered_df['num_forecast'] = filtered_df['Consensus'].apply(extract_numeric)
            filtered_df['num_previous'] = filtered_df['Previous'].apply(extract_numeric)

            # Shift previous values to calculate changes
            filtered_df['previous_previous'] = filtered_df['num_previous'].shift(1)

            # Calculate percentage changes
            filtered_df = calculate_percentage_changes(filtered_df)

            temp_data.append(filtered_df)

        if temp_data:
            combined_result = combine_dataframes(temp_data).sort_values(by='datetime')
            if not combined_result.empty:
                all_results[currency] = combined_result

    return all_results


def calculate_percentage_changes(df):
    """Calculate percentage change for Actual, Consensus, and Previous values."""

    def calc_percentage_change(current, previous):
        """Calculate percentage change, avoiding division by zero."""
        if previous and previous != 0:  
            return (current - previous) / abs(previous)
        return 0  

    # Ensure numeric columns have no NaN values
    df[['num_actual', 'num_forecast', 'num_previous', 'previous_previous']] = df[
        ['num_actual', 'num_forecast', 'num_previous', 'previous_previous']
    ].fillna(0)

    # Apply calculations while handling percentage values correctly
    df['actual_percentage'] = df.apply(
        lambda row: row['num_actual'] if "%" in str(row['Actual']) else calc_percentage_change(row['num_actual'], row['num_previous']), axis=1
    )

    df['forecast_percentage'] = df.apply(
        lambda row: row['num_forecast'] if "%" in str(row['Consensus']) else calc_percentage_change(row['num_forecast'], row['num_previous']), axis=1
    )

    df['previous_percentage'] = df.apply(
        lambda row: row['num_previous'] if "%" in str(row['Previous']) else calc_percentage_change(row['num_previous'], row['previous_previous']), axis=1
    )

    return df

def get_current_year():
  """Returns the current year as an integer."""
  return datetime.datetime.now().year

def calculate_and_rescale_score(df):
    # Surprise Component: Actual - Forecast
    df['Surprise'] = df['actual_percentage'] - df['forecast_percentage']
    
    # Trend Component: Actual - Previous
    df['Trend'] = df['actual_percentage'] - df['previous_percentage']
    
    # Magnitude Component: |Surprise| + |Trend|
    df['Magnitude'] = np.abs(df['Surprise']) + np.abs(df['Trend'])
    
    # Weights (all set to 1 as per your example)
    alpha = 1
    beta = 1
    gamma = 1
    
    # Score = α*Surprise + ß*Trend + ΓMagnitude
    df['Score'] = alpha * df['Surprise'] + beta * df['Trend'] + gamma * df['Magnitude']
    
    # Normalize the Score to the range of -20 to 20
    min_score = df['Score'].min()
    max_score = df['Score'].max()
    
    # Handle edge case where all scores are the same
    if max_score - min_score == 0:
        df['Rescaled Score'] = 0  # or you can set it to np.nan
    else:
        # Mapping to -20 to 20
        df['Rescaled Score'] = np.where(
            df['Score'] < 0,
            -20 + ((df['Score'] - min_score) * (0 - (-20))) / (max_score - min_score),
            0 + ((df['Score'] - 0) * (20 - 0)) / (max_score - 0)
        )
    
    # Round the Rescaled Score to 2 decimal places
    df['Rescaled Score'] = df['Rescaled Score'].round(2)

    # Normalize the Trend to the range of -20 to 20
    min_trend = df['Trend'].min()
    max_trend = df['Trend'].max()
    
    # Handle edge case where all trends are the same
    if max_trend - min_trend == 0:
        df['Rescaled Trend'] = 0  # or you can set it to np.nan
    else:
        # Mapping to -20 to 20
        df['Rescaled Trend'] = np.where(
            df['Trend'] < 0,
            -20 + ((df['Trend'] - min_trend) * (0 - (-20))) / (max_trend - min_trend),
            0 + ((df['Trend'] - 0) * (20 - 0)) / (max_trend - 0)
        )

    df['year'] = df['datetime'].dt.year
    df['month'] = df['datetime'].dt.month
    
    # Calculate avg_score grouped by event and month
    new_score = df.groupby(['event', 'month'])['Score'].mean().reset_index()
    new_score.rename(columns={'Score': 'avg_score'}, inplace=True)
    df = pd.merge(df, new_score, on=['event', 'month'], how='left')

    # Normalize the avg_score in the range -20 to 20
    min_avg_score = df['avg_score'].min()
    max_avg_score = df['avg_score'].max()

    # Handle edge case where all avg_score values are the same
    if max_avg_score - min_avg_score == 0:
        df['rescaled_avg_score'] = 0  # or you can set it to np.nan
    else:
        # Mapping avg_score to -20 to 20
        df['rescaled_avg_score'] = np.where(
            df['avg_score'] < 0,
            -20 + ((df['avg_score'] - min_avg_score) * (0 - (-20))) / (max_avg_score - min_avg_score),
            0 + ((df['avg_score'] - 0) * (20 - 0)) / (max_avg_score - 0)
        )

    # Round the rescaled values to 2 decimal places
    df['Rescaled Trend'] = df['Rescaled Trend'].round(2)
    df['Rescaled Score'] = df['Rescaled Score'].round(2)
    df['rescaled_avg_score'] = df['rescaled_avg_score'].round(2)

    # Round the raw Score to 2 decimal places
    df['Score'] = df['Score'].round(2)

    return df


def calculate_score_with_weights(df):
    """
    Calculate scores using weights for each indicator.

    Args:
        df (pd.DataFrame): DataFrame containing forecast, actual, and indicator columns.

    Returns:
        pd.DataFrame: DataFrame with calculated scores and rescaled scores.
    """
    # Define weights for each indicator
    

    # Ensure weights sum to 1 for consistent scoring
    

    # Calculate score based on (forecast - actual) * weight
    df['Score'] = df.apply(
        lambda row: (row['forecast_percentage'] - row['actual_percentage']) * weights.get(row['ev'], 0), axis=1
    )
    df['Surprise'] = df['actual_percentage'] - df['forecast_percentage']
    
    # Trend Component: Actual - Previous
    df['Trend'] = df['actual_percentage'] - df['previous_percentage']
    
    # Magnitude Component: |Surprise| + |Trend|
    df['Magnitude'] = np.abs(df['Surprise']) + np.abs(df['Trend'])

    # Normalize the Score to the range of -20 to 20
    min_score = df['Score'].min()
    max_score = df['Score'].max()

    # Handle edge case where all scores are the same
    if max_score - min_score == 0:
        df['Rescaled Score'] = 0  # or you can set it to np.nan
    else:
        # Map scores to -20 to 20
        df['Rescaled Score'] = -20 + ((df['Score'] - min_score) * (40)) / (max_score - min_score)

    # Round the Rescaled Score to 2 decimal places
    df['Rescaled Score'] = df['Rescaled Score'].round(2)

    # Add year and month columns for grouping
    df['year'] = df['datetime'].dt.year
    df['month'] = df['datetime'].dt.month

    # Calculate avg_score grouped by indicator and month
    new_score = df.groupby(['Event', 'month'])['Score'].mean().reset_index()
    new_score.rename(columns={'Score': 'avg_score'}, inplace=True)
    df = pd.merge(df, new_score, on=['Event', 'month'], how='left')

    # Normalize the avg_score to -20 to 20
    min_avg_score = df['avg_score'].min()
    max_avg_score = df['avg_score'].max()

    # Handle edge case where all avg_score values are the same
    if max_avg_score - min_avg_score == 0:
        df['rescaled_avg_score'] = 0  # or you can set it to np.nan
    else:
        # Map avg_score to -20 to 20
        df['rescaled_avg_score'] = -20 + ((df['avg_score'] - min_avg_score) * (40)) / (max_avg_score - min_avg_score)

    # Round the rescaled avg_score to 2 decimal places
    df['rescaled_avg_score'] = df['rescaled_avg_score'].round(2)
    df['Rescaled Trend'] = 0 
    df['Trend'] = 0

    return df



def save_analyzed_data(analyzed_result):
    for currency_name, df in analyzed_result.items():
        # Get or create the currency
        currency, _ = Currency.objects.get_or_create(name=currency_name)
        
        for _, row in df.iterrows():
            # Ensure that str_date and time are populated
            str_date = row['datetime'].strftime('%d/%m/%Y')  # Assuming datetime is a pandas Timestamp
            time = row['datetime'].strftime('%H:%M')  # Extracting just the time part
            # Get or create the event
            event, _ = Event.objects.get_or_create(
                currency=currency,
                event_code=row['ev'],
                importance=row['Impact']
            )
            
            # Use filter to handle potential duplicates
            event_data_entries = EventData.objects.filter(
                event=event,
                date=row['datetime'],
                time=time
            )
            
            if event_data_entries.count() > 1:
                # Log a warning and delete duplicates, keeping the first entry
                print(f"Warning: Found {event_data_entries.count()} duplicates for {event.event_code} on {row['date']} at {row['time']}. Deleting extras.")
                for duplicate in event_data_entries[1:]:
                    duplicate.delete()
            
            # Use the first entry if it exists, or None if no entries exist
            event_data = event_data_entries.first()
            
            # Prepare data for comparison or creation
            data_to_save = {
                'actual': row['num_actual'] if row['num_actual'] is not None else 0.0,
                'forecast': row['num_forecast'] if row['num_forecast'] is not None else 0.0,
                'previous': row['num_previous'] if row['num_previous'] is not None else 0.0,
                'actual_perc': row['actual_percentage'] if row['actual_percentage'] is not None else 0.0,
                'forecast_perc': row['forecast_percentage'] if row['forecast_percentage'] is not None else 0.0,
                'previous_perc': row['previous_percentage'] if row['previous_percentage'] is not None else 0.0,
                'surprise': row['Surprise'] if row['Surprise'] is not None else 0.0,
                'trend': row['Trend'] if row['Trend'] is not None else 0.0,
                'magnitude': row['Magnitude'] if row['Magnitude'] is not None else 0.0,
                'score': row['Score'] if row['Score'] is not None else 0.0,
                'rescaled_score': row['Rescaled Score'] if row['Rescaled Score'] is not None else 0.0,
                'rescaled_trend': row['Rescaled Trend'] if row['Rescaled Trend'] is not None else 0.0,
                'rescaled_avg_score': row['rescaled_avg_score'] if row['rescaled_avg_score'] is not None else 0.0,
                'year': row['year'],
                'month': row['month'],
                'avg_score': row['avg_score'] if row['avg_score'] is not None else 0.0,
            }

            
            
            # Add these to data_to_save
            #data_to_save['str_date'] = str_date
            #data_to_save['time'] = time
            #data_to_save['date'] = row['datetime']

            if event_data:
                # Compare fields to determine if an update is needed
                should_update = any(
                    getattr(event_data, key) != value
                    for key, value in data_to_save.items()
                )
                
                if should_update:
                    # Update the existing EventData entry
                    for key, value in data_to_save.items():
                        setattr(event_data, key, value)
                    event_data.save()
                    print(f"Updated EventData for {event.event_code} on {str_date} at {time}.")
                else:
                    print(f"No changes detected for {event.event_code} on {str_date} at {time}. Skipping update.")
            else:
                # Create a new EventData entry
                EventData.objects.create(
                    event=event,
                    date=row['datetime'],
                    str_date=str_date,
                    time=time,
                    **data_to_save
                )
                print(f"Created new EventData for {event.event_code} on {str_date} at {time}.")

def main():
    print("#### Fetching Data ####")
    combined = fetch_data()
    #combined = combined.drop_duplicates(subset='id')
    print("### Filtering ###")
    res = filter_data(target,combined)
    analyzed_result = {}
    print("### Analyzing ###")
    for curr in target:
        curr_data = res[curr]
        sorted_data = curr_data.sort_values('datetime')
        analyzed = calculate_score_with_weights(sorted_data)
        analyzed_result[curr] = analyzed
    print("### Saving ###")
    save_analyzed_data(analyzed_result)