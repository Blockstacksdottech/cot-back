import cot_reports as cot
import pandas as pd
import numpy as np
import json
from .models import DateInterval, Data, GeneralData
from django.utils.timezone import make_aware

symbol_mapping = {
    'USD INDEX - ICE FUTURES U.S.': 'USD',
    'EURO FX - CHICAGO MERCANTILE EXCHANGE': 'EURUSD',
    'GOLD - COMMODITY EXCHANGE INC.': 'GOLD',
    'BRITISH POUND - CHICAGO MERCANTILE EXCHANGE': 'GBP',
    'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE': 'JPYDEX',
    'EURO FX/BRITISH POUND XRATE - CHICAGO MERCANTILE EXCHANGE': 'EURGBP',
    'CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'CAD',
    'SWISS FRANC - CHICAGO MERCANTILE EXCHANGE': 'CHF',
    'NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'NZDUSD',
    'MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE': 'MXNP'
}


def filter_tff_df(final_data):
    # Filter the TFF report
    tff_report = final_data.copy()
    tff_report = tff_report[tff_report['Market_and_Exchange_Names'].isin(
        symbol_mapping.keys())].copy()
    important_columns_tff = [
        'Market_and_Exchange_Names',
        'Report_Date_as_YYYY-MM-DD',
        'Open_Interest_All',
        'Dealer_Positions_Long_All',
        'Dealer_Positions_Short_All',
        'Asset_Mgr_Positions_Long_All',
        'Asset_Mgr_Positions_Short_All',
        'Lev_Money_Positions_Long_All',
        'Lev_Money_Positions_Short_All',
        'Other_Rept_Positions_Long_All',
        'Other_Rept_Positions_Short_All',
        'Tot_Rept_Positions_Long_All',
        'Tot_Rept_Positions_Short_All',
        'NonRept_Positions_Long_All',
        'NonRept_Positions_Short_All',
        'Conc_Gross_LE_4_TDR_Long_All',
        'Conc_Gross_LE_4_TDR_Short_All',
        'Conc_Gross_LE_8_TDR_Long_All',
        'Conc_Gross_LE_8_TDR_Short_All',
        'Conc_Net_LE_4_TDR_Long_All',
        'Conc_Net_LE_4_TDR_Short_All',
        'Conc_Net_LE_8_TDR_Long_All',
        'Conc_Net_LE_8_TDR_Short_All',
        'date'
    ]

    # Filter the dataframe
    filtered_tff_df = tff_report[important_columns_tff]
    filtered_tff_df['Symbol'] = filtered_tff_df['Market_and_Exchange_Names'].map(
        symbol_mapping)
    return filtered_tff_df


def analyze_tff_df(tff_df):
    # Convert date to datetime format if necessary
    tff_df['Report_Date_as_YYYY-MM-DD'] = pd.to_datetime(
        tff_df['Report_Date_as_YYYY-MM-DD'])

    # Sort by date to ensure correct calculations
    tff_df = tff_df.sort_values(by='Report_Date_as_YYYY-MM-DD')

    # Calculate total positions and percentages for commercial and non-commercial
    tff_df['Comm_Long'] = tff_df['Dealer_Positions_Long_All']
    tff_df['Comm_Short'] = tff_df['Dealer_Positions_Short_All']
    tff_df['Comm_Total'] = tff_df['Comm_Long'] + tff_df['Comm_Short']
    tff_df['Comm_Long_%'] = (tff_df['Comm_Long'] / tff_df['Comm_Total']) * 100
    tff_df['Comm_Short_%'] = (
        tff_df['Comm_Short'] / tff_df['Comm_Total']) * 100
    tff_df['Comm_Net_Position'] = tff_df['Comm_Long'] - tff_df['Comm_Short']

    tff_df['NonComm_Long'] = tff_df['Lev_Money_Positions_Long_All']
    tff_df['NonComm_Short'] = tff_df['Lev_Money_Positions_Short_All']
    tff_df['NonComm_Total'] = tff_df['NonComm_Long'] + tff_df['NonComm_Short']
    tff_df['NonComm_Long_%'] = (
        tff_df['NonComm_Long'] / tff_df['NonComm_Total']) * 100
    tff_df['NonComm_Short_%'] = (
        tff_df['NonComm_Short'] / tff_df['NonComm_Total']) * 100
    tff_df['NonComm_Net_Position'] = tff_df['NonComm_Long'] - \
        tff_df['NonComm_Short']

    # Calculate differences compared to the previous week
    tff_df['Comm_Long_Change'] = tff_df['Comm_Long'].diff()
    tff_df['Comm_Short_Change'] = tff_df['Comm_Short'].diff()
    tff_df['Comm_Net_Position_Change'] = tff_df['Comm_Net_Position'].diff()

    tff_df['NonComm_Long_Change'] = tff_df['NonComm_Long'].diff()
    tff_df['NonComm_Short_Change'] = tff_df['NonComm_Short'].diff()
    tff_df['NonComm_Net_Position_Change'] = tff_df['NonComm_Net_Position'].diff()

    tff_df['Comm_Long_Change_%'] = (
        tff_df['Comm_Long_Change'] / tff_df['Comm_Long'].shift(1)) * 100
    tff_df['Comm_Short_Change_%'] = (
        tff_df['Comm_Short_Change'] / tff_df['Comm_Short'].shift(1)) * 100
    tff_df['NonComm_Long_Change_%'] = (
        tff_df['NonComm_Long_Change'] / tff_df['NonComm_Long'].shift(1)) * 100
    tff_df['NonComm_Short_Change_%'] = (
        tff_df['NonComm_Short_Change'] / tff_df['NonComm_Short'].shift(1)) * 100

    # Determine sentiment for commercial and non-commercial positions
    tff_df['Comm_Sentiment'] = np.where(
        tff_df['Comm_Net_Position'] > 0, 'Long Dominated', 'Short Dominated')
    tff_df['NonComm_Sentiment'] = np.where(
        tff_df['NonComm_Net_Position'] > 0, 'Long Dominated', 'Short Dominated')

    # Fill NaN values with 0
    tff_df = tff_df.fillna(0)

    # Display results
    return tff_df


def filter_and_analyze_tff_data(final_data):
    tff_df = filter_tff_df(final_data)
    analyzed_tff_df = analyze_tff_df(tff_df)
    # print(analyzed_tff_df.head()[["Symbol", "Decision", 'Sentiment_Score', 'Crowded_Long_Positions', 'Crowded_Short_Positions']])
    return analyzed_tff_df

# Example call to the function
# filter_and_analyze_tff_data(final_data)


# helper
def format_date(date_str):
    date_str = str(date_str)
    date_str = ("0" * (6 - len(date_str)))+date_str
    # Assuming century information is missing in the first 2 digits
    year = int(date_str[:2]) + 2000
    month = int(date_str[2:4])
    day = int(date_str[4:])
    return pd.to_datetime(f"{year}-{month:02d}-{day:02d}")

# partial fetching function


def fetch_cot_data(start_year, end_year, cot_type, date_header):
    df = pd.DataFrame()
    for i in range(start_year, end_year + 1):
        try:
            single_year = pd.DataFrame(
                cot.cot_year(i, cot_report_type=cot_type))
            single_year['date'] = single_year[date_header].apply(format_date)
            # df.append(single_year, ignore_index=True)
            df = pd.concat([df, single_year], ignore_index=True)
        except Exception as e:
            print(e)
            continue
    df = df.sort_values(by=date_header, ascending=False)
    return df

# main grouping function


def main(start_year, end_year):
    reports_type = ['traders_in_financial_futures_fut']
    date_header = ['As_of_Date_In_Form_YYMMDD']
    final_data = []
    index = 0
    for c_type in reports_type:
        print(f"########## fetching {c_type} ##########")
        data = fetch_cot_data(start_year, end_year, c_type, date_header[index])
        final_data.append(data)
        index += 1
    return final_data


def dataframe_to_json(dataframe):
    return dataframe.to_json(orient='records')


def save_to_django_models(symbol_dataframes):
    for symbol, dataframe in symbol_dataframes.items():
        json_data = dataframe_to_json(dataframe)
        data_list = json.loads(json_data)

        for data in data_list:
            try:
                date = data['date']
                symbol = data["Symbol"]
                date_obj = make_aware(pd.to_datetime(date, unit='ms'))

                date_interval, created = DateInterval.objects.get_or_create(
                    date=date_obj)
                date_interval.save()

                if GeneralData.objects.filter(date_interval=date_interval, symbol=symbol).exists():
                    print(
                        f"Entry for {symbol} on {date_obj} already exists. Skipping...")
                    continue

                # Ensure all necessary fields are available and handle edge cases
                comm_long = data.get('Comm_Long', 0) or 0
                comm_short = data.get('Comm_Short', 0) or 0
                comm_total = data.get('Comm_Total', 0) or 0
                comm_long_pct = data.get('Comm_Long_%', 0) or 0
                comm_short_pct = data.get('Comm_Short_%', 0) or 0
                comm_net_position = data.get('Comm_Net_Position', 0) or 0
                comm_long_change = data.get('Comm_Long_Change', 0) or 0
                comm_short_change = data.get('Comm_Short_Change', 0) or 0
                comm_net_position_change = data.get(
                    'Comm_Net_Position_Change', 0) or 0
                comm_long_change_pct = data.get('Comm_Long_Change_%', 0) or 0
                comm_short_change_pct = data.get('Comm_Short_Change_%', 0) or 0
                comm_sentiment = data.get('Comm_Sentiment', 'Neutral')
                noncomm_long = data.get('NonComm_Long', 0) or 0
                noncomm_short = data.get('NonComm_Short', 0) or 0
                noncomm_total = data.get('NonComm_Total', 0) or 0
                noncomm_long_pct = data.get('NonComm_Long_%', 0) or 0
                noncomm_short_pct = data.get('NonComm_Short_%', 0) or 0
                noncomm_net_position = data.get('NonComm_Net_Position', 0) or 0
                noncomm_long_change = data.get('NonComm_Long_Change', 0) or 0
                noncomm_short_change = data.get('NonComm_Short_Change', 0) or 0
                noncomm_net_position_change = data.get(
                    'NonComm_Net_Position_Change', 0) or 0
                noncomm_long_change_pct = data.get(
                    'NonComm_Long_Change_%', 0) or 0
                noncomm_short_change_pct = data.get(
                    'NonComm_Short_Change_%', 0) or 0
                noncomm_sentiment = data.get('NonComm_Sentiment', 'Neutral')

                # Calculate percentage change for comm_long_change_pct if not provided
                if comm_long != 0:
                    comm_long_change_pct = (comm_long_change / comm_long) * 100
                else:
                    comm_long_change_pct = 0

                general_data = GeneralData.objects.create(
                    date_interval=date_interval,
                    symbol=symbol,
                    comm_long=comm_long,
                    comm_short=comm_short,
                    comm_total=comm_total,
                    comm_long_pct=comm_long_pct,
                    comm_short_pct=comm_short_pct,
                    comm_net_position=comm_net_position,
                    comm_long_change=comm_long_change,
                    comm_short_change=comm_short_change,
                    comm_net_position_change=comm_net_position_change,
                    comm_long_change_pct=comm_long_change_pct,
                    comm_short_change_pct=comm_short_change_pct,
                    comm_sentiment=comm_sentiment,
                    noncomm_long=noncomm_long,
                    noncomm_short=noncomm_short,
                    noncomm_total=noncomm_total,
                    noncomm_long_pct=noncomm_long_pct,
                    noncomm_short_pct=noncomm_short_pct,
                    noncomm_net_position=noncomm_net_position,
                    noncomm_long_change=noncomm_long_change,
                    noncomm_short_change=noncomm_short_change,
                    noncomm_net_position_change=noncomm_net_position_change,
                    noncomm_long_change_pct=noncomm_long_change_pct,
                    noncomm_short_change_pct=noncomm_short_change_pct,
                    noncomm_sentiment=noncomm_sentiment
                )
                general_data.save()
                print("saved")
            except Exception as e:
                print(e)
                input(data)


def regroup_by_symbol(important_data):
    # Group the dataframe by 'Symbol'
    grouped_data = important_data.groupby('date')

    # Create a dictionary to store dataframes for each symbol
    symbol_dataframes = {}

    # Iterate through the groups and store each group's dataframe in the dictionary
    for symbol, group in grouped_data:
        symbol_dataframes[symbol] = group.reset_index(drop=True)

    return symbol_dataframes


def execute():
    start_year = 2005
    end_year = 2024
    final_data = main(start_year, end_year)
    analyzed_data = filter_and_analyze_tff_data(final_data[0])
    important_data = analyzed_data[[
        'date',  # Date of the report
        "Symbol",
        'Comm_Long',  # Commercial long positions
        'Comm_Short',  # Commercial short positions
        'Comm_Total',  # Total commercial positions
        'Comm_Long_%',  # Percentage of commercial long positions
        'Comm_Short_%',  # Percentage of commercial short positions
        'Comm_Net_Position',  # Net commercial positions
        'Comm_Long_Change',  # Change in commercial long positions compared to last week
        'Comm_Short_Change',  # Change in commercial short positions compared to last week
        # Change in net commercial positions compared to last week
        'Comm_Net_Position_Change',
        # Percentage change in commercial long positions compared to last week
        'Comm_Long_Change_%',
        # Percentage change in commercial short positions compared to last week
        'Comm_Short_Change_%',
        # Sentiment for commercial positions (Long Dominated/Short Dominated)
        'Comm_Sentiment',
        'NonComm_Long',  # Non-commercial long positions
        'NonComm_Short',  # Non-commercial short positions
        'NonComm_Total',  # Total non-commercial positions
        'NonComm_Long_%',  # Percentage of non-commercial long positions
        'NonComm_Short_%',  # Percentage of non-commercial short positions
        'NonComm_Net_Position',  # Net non-commercial positions
        'NonComm_Long_Change',  # Change in non-commercial long positions compared to last week
        'NonComm_Short_Change',  # Change in non-commercial short positions compared to last week
        # Change in net non-commercial positions compared to last week
        'NonComm_Net_Position_Change',
        # Percentage change in non-commercial long positions compared to last week
        'NonComm_Long_Change_%',
        # Percentage change in non-commercial short positions compared to last week
        'NonComm_Short_Change_%',
        # Sentiment for non-commercial positions (Long Dominated/Short Dominated)
        'NonComm_Sentiment'
    ]]
    symbol_dataframes = regroup_by_symbol(important_data)
    save_to_django_models(symbol_dataframes)
