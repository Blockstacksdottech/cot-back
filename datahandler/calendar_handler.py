from .models import *
import investpy
import datetime
import re
import numpy as np
import pandas as pd
from .events_const import final_values,target,zone_mapping,weights
import time

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
    arr = get_month_range(START_DATE,get_current_date())
    all_data = []
    for i in range(len(arr) - 1):
        print(arr[i])
        while True:
            try:
                data = investpy.economic_calendar(from_date=arr[i],to_date=arr[i+1])
                break
            except Exception as e:
                print("Failed Fetching data retrying in 5 sec")
                time.sleep(5)

        all_data.append(data)
    combined = combine_dataframes(all_data)
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
    # Create a dictionary to store results for each currency
    all_results = {}

    # Loop over each target currency and apply filtering
    for currency in target_currencies:
        # Get the regex pattern for the current currency
        temp_data = []
        for k in final_values.keys():
            options = final_values[k]
            if currency in options:
                q = options[currency]
            else:
                q = options.get('all', '')

            # Filter the DataFrame for the specific currency
            test_data = combined_df[combined_df['currency'] == currency]

            # Further filter for 'importance' levels (if needed)
            test_data = test_data[test_data['importance'].isin(['low', 'medium', 'high'])]
            test_data = test_data[test_data['zone'].isin([zone_mapping[currency]])]

            # Apply the regex filter on the 'event' column
            filtered_df = test_data[test_data['event'].str.contains(q, case=False, regex=True)]
            filtered_df['time'] = filtered_df['time'].replace('Tentative', '00:00')
            filtered_df['datetime'] = pd.to_datetime(filtered_df['date'] + ' ' + filtered_df['time'], format='%d/%m/%Y %H:%M')
            filtered_df['ev'] = k
            filtered_df = filtered_df.sort_values(by='date')
            # Order the filtered results by date
            filtered_df = filtered_df.sort_values(by='datetime')

            # Apply the extract_numeric function to clean up the values
            filtered_df['num_actual'] = filtered_df['actual'].apply(extract_numeric)
            filtered_df['num_forecast'] = filtered_df['forecast'].apply(extract_numeric)
            filtered_df['num_previous'] = filtered_df['previous'].apply(extract_numeric)
            # Shift the 'previous' column to get the value from the prior row (previous_previous)
            filtered_df['previous_previous'] = filtered_df['num_previous'].shift(1)
            #print(filtered_df['event'].unique().tolist())
            #print(filtered_df.tail())
            # Now calculate percentage changes for actual and forecast based on previous
            filtered_df = calculate_percentage_changes(filtered_df)
            temp_data.append(filtered_df)

        combined_result = combine_dataframes(temp_data)
        # Order the filtered results by date
        combined_result = combined_result.sort_values(by='datetime')

        # Apply the extract_numeric function to clean up the values
        #combined_result['num_actual'] = combined_result['actual'].apply(extract_numeric)
        #combined_result['num_forecast'] = combined_result['forecast'].apply(extract_numeric)
        #combined_result['num_previous'] = combined_result['previous'].apply(extract_numeric)
         # Shift the 'previous' column to get the value from the prior row (previous_previous)
        #df['previous_previous'] = df['num_previous'].shift(1)
        # Now calculate percentage changes for actual and forecast based on previous
        #combined_result = calculate_percentage_changes(combined_result)

        # Store the results for the current currency if any are found
        if not combined_result.empty:
            all_results[currency] = combined_result

    return all_results

def calculate_percentage_changes(df):
    """Calculate percentage change for actual, forecast, and previous based on previous and previous_previous."""
    
    def calc_percentage_change(current, previous):
        """Helper function to calculate percentage change."""
        if previous != 0:  # Avoid division by zero
            return ((current - previous) / abs(previous))
        return 0  # If previous is 0, return 0 to avoid errors


    # Calculate percentage change for 'actual' and 'forecast' based on 'previous'
    df['actual_percentage'] = df.apply(
        lambda row: calc_percentage_change(row['num_actual'], row['num_previous']) if "%" not in str(row['actual']) else row['num_actual'], axis=1
    )
    
    df['forecast_percentage'] = df.apply(
        lambda row: calc_percentage_change(row['num_forecast'], row['num_previous']) if "%" not in str(row['forecast'])  else row['num_forecast'], axis=1
    )
    
   
    
    # Calculate the percentage change for 'previous' based on 'previous_previous'
    df['previous_percentage'] = df.apply(
        lambda row: calc_percentage_change(row['num_previous'], row['previous_previous']) if pd.notnull(row['previous_previous']) and "%" not in str(row['previous'])  else row['num_previous'], axis=1
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
    new_score = df.groupby(['event', 'month'])['Score'].mean().reset_index()
    new_score.rename(columns={'Score': 'avg_score'}, inplace=True)
    df = pd.merge(df, new_score, on=['event', 'month'], how='left')

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
            # Get or create the event
            event, _ = Event.objects.get_or_create(currency=currency, event_code=row['ev'], importance=row['importance'])

            # Check if the EventData already exists
            event_data_exists = EventData.objects.filter(
                event=event,
                date=row['datetime'],
                time=row['time']
            ).exists()

            if not event_data_exists:
                # Create EventData entry
                EventData.objects.create(
                    event=event,
                    date=row['datetime'],
                    str_date=row['date'],
                    time=row['time'],
                    actual=row['num_actual'] if row['num_actual'] is not None else 0.0,
                    forecast=row['num_forecast'] if row['num_forecast'] is not None else 0.0,
                    previous=row['num_previous'] if row['num_previous'] is not None else 0.0,
                    actual_perc=row['actual_percentage'] if row['actual_percentage'] is not None else 0.0,
                    forecast_perc=row['forecast_percentage'] if row['forecast_percentage'] is not None else 0.0,
                    previous_perc=row['previous_percentage'] if row['previous_percentage'] is not None else 0.0,
                    surprise=row['Surprise'] if row['Surprise'] is not None else 0.0,
                    trend=row['Trend'] if row['Trend'] is not None else 0.0,
                    magnitude=row['Magnitude'] if row['Magnitude'] is not None else 0.0,
                    score=row['Score'] if row['Score'] is not None else 0.0,
                    rescaled_score=row['Rescaled Score'] if row['Rescaled Score'] is not None else 0.0,
                    rescaled_trend=row['Rescaled Trend'] if row['Rescaled Trend'] is not None else 0.0,
                    rescaled_avg_score=row['rescaled_avg_score'] if row['rescaled_avg_score'] is not None else 0.0,
                    year=row['year'],
                    month=row['month'],
                    avg_score=row['avg_score'] if row['avg_score'] is not None else 0.0,
                )
            else:
                print(f"EventData for {event.event_code} on {row['date']} at {row['time']} already exists.")


def main():
    print("#### Fetching Data ####")
    combined = fetch_data()
    combined = combined.drop_duplicates(subset='id')
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